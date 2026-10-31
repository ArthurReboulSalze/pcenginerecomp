"""Authored admission controls; fixture literals are not emulator receipts."""
import copy
from pathlib import Path
import tempfile
import unittest
from scripts import active_irq_qualify as qualification
from pcerecomp.abi import ABI
from tests.active_irq_fixture import cases,program


def phase(kernel=False):
    result={key:0 for key in(qualification.KERNEL_KEYS if kernel else qualification.PHASE_KEYS)}
    result.update(hpos=100,vpos=30,hstate=1,vstate=1,hremaining=100,raster=12,
        sprite_count=2,bg_start=80,bg_end=500,hsync=0,latched_cr=196,
        latched_mwr=3,cr=196,mwr=3,rcr=96,divider=3)
    if kernel:result.update(p=1,mask=4,irr=3,sample=3,status=68,read_pending=1,
        read_buffer=0xa65c,marr=0x6002,mawr=0x6003,half=1,end=1,length=1,
        cd_enabled=12,cd_active=12,write_address=65535)
    return result


def authored_clock_group():
    """Synthetic topology ledger, not a recorded device trace or execution.

    TAI2 has four original calls but retires one instruction. Its first
    dynamic read grant is followed by a legitimate nonwaiting prefetch grant.
    """
    case=next(c for c in cases()if c['source']=='raster'and c['access']=='tai'
              and c['policy']=='retain'and c['divisor']==3 and c['vce']==3)
    markers=program(case)[1]
    source=next(row for row in program(case)[2]if row['pc']==markers['target'])
    spans=[];tick=1000;hpos=100
    for duration,waiting in((42,0),(6,0),(3,1),(18,0),(6,0),(18,0),(33,0)):
        spans.append([tick,duration,tick+duration,waiting,3,3,hpos,30,1,1])
        tick+=duration;hpos+=duration
    edges=[]
    for index in(2,4):
        before=phase(True);before['hpos']=spans[index][6]
        after=copy.deepcopy(before);after.update(read_pending=0,status=4,hpos=before['hpos']+spans[index][1])
        edges.append(dict(span=index,kinds=6,before=before,after=after))
    values=[0]*42;values[7]=tick
    row=dict(pc=source['pc'],mpr=source['mpr'],physical=source['physical'],bytes=source['data'],
        before=[2,0,0,255,1,0,1,1,1,1,0,1,0,0],ticks=126,internal=15,
        wait_ticks=3,vector=0xfff8,causes=0,active_before=phase(True),
        clocks=spans,call_rows=[[1,42,0,0,0,0,1,0,0,0],
            [2,27,9,0,1,3,4,3,0,0],[3,24,6,0,4,5,6,0,0,0],
            [4,33,0,1,6,6,7,0,1,0]],
        callbacks=[[4,spans[-1][0],1,0xfff8,markers['return_pc'],4]],
        edges=edges,after=dict(values=values))
    return case,markers,row

class ActiveIrqReferenceTests(unittest.TestCase):
    def test_complete_source_space_has_48_distinct_recipes(self):
        matrix=cases()
        self.assertEqual(len(matrix),48)
        self.assertEqual(len({case['id']for case in matrix}),48)

    def test_full_mapping_bytes_and_integer_hits_are_strict(self):
        case=cases()[0];row=dict(program(case)[2][0],hits=1)
        qualification.validate_hits([row],case)
        for page in range(8):
            bad=copy.deepcopy(row);bad['mpr'][page]^=1
            with self.subTest(page=page),self.assertRaises(ValueError):qualification.validate_hits([bad],case)
        for bad_hits in(True,0,-1,1.0):
            bad=dict(row,hits=bad_hits)
            with self.assertRaises(ValueError):qualification.validate_hits([bad],case)

    def test_written_duplicate_and_nonfinite_json_refuse(self):
        with tempfile.TemporaryDirectory()as temporary:
            path=Path(temporary)/'bad.json'
            for text in('{"schema":1,"schema":1}','{"schema":NaN}','{"schema":1e999}'):
                path.write_text(text)
                with self.subTest(text=text),self.assertRaises(ValueError):qualification.load(path)

    def test_phase_kernel_types_and_hardware_field_widths(self):
        qualification.validate_phase(phase())
        qualification.validate_phase(phase(True),True)
        for key,value in(('read_pending',2),('half',True),('write_address',65536),
                          ('read_buffer',2**48),('p',256),('sample',8),
                          ('delay',2**31),('hpos',1365),('hremaining',2**31),
                          ('hstate',4),('vstate',-1),('sprite_count',17)):
            bad=phase(True);bad[key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):
                qualification.validate_phase(bad,True)
        # The observer preserves signed arithmetic fields; it does not cast
        # them into fabricated uint64 phase values.
        signed=phase(True);signed['delay']=-1
        qualification.validate_phase(signed,True)
        bad=phase();bad['carry']=True
        with self.assertRaises(ValueError):qualification.validate_phase(bad)

    def test_independent_wrapped_read_sector_and_stack_literals(self):
        ram=qualification.expected_ram()
        self.assertEqual(len(ram),65536)
        self.assertEqual(ram[65534:],[0x53,0x64])
        self.assertEqual(ram[0],0x75)
        self.assertEqual(ram[2046:65534],[0]*63488)
        for source,last_a in(('raster',2),('collision',0x60)):
            case=next(c for c in cases()if c['source']==source)
            self.assertEqual(qualification.stack_literal(case,cut=0)[253:],[0,last_a,0])
            stack=qualification.stack_literal(case,cut=1)
            ret=program(case)[1]['return_pc']
            self.assertEqual(stack[252:],[0,129,ret&255,ret>>8])

    def test_original_continuations_are_not_retired_instructions(self):
        case=next(c for c in cases()if c['access']=='tai')
        plan=program(case)[2]
        setup=next(row for row in plan if row['data'][0]==0x73)
        target=next(row for row in plan if row['data'][0]==0xf3)
        scalar=plan[0]
        self.assertEqual(setup['data'][5:],[100,0])
        hits=qualification.validate_hits([dict(setup,hits=1),dict(target,hits=1),dict(scalar,hits=2)],case)
        work=dict(instructions=4,calls=108,clock_calls=108,clock_ticks=999,
            irqs=0,rtis=0,blocks=2,block_bytes=102,adpcm_cause_groups=0,
            vdc_cause_groups=0,wait_ticks=0)
        qualification.validate_work(work,hits,999,True)
        for key,value in(('instructions',108),('calls',4),('blocks',3),('block_bytes',101),('clock_ticks',998)):
            with self.subTest(key=key),self.assertRaises(ValueError):
                qualification.validate_work(dict(work,**{key:value}),hits,999,True)
        tool=dict(work,calls=4,clock_calls=0)
        qualification.validate_work(tool,hits,999,False)

    def test_first_dynamic_grant_accepts_later_nonwaiting_prefetch_grant(self):
        case,markers,row=authored_clock_group()
        result=qualification.validate_clock_group(row,case,markers)
        self.assertEqual(result,dict(dynamic_grants=1,hardware_callbacks=7))

    def test_written_clock_tampering_refuses_without_phase_alignment(self):
        case,markers,row=authored_clock_group()
        changes=[lambda r:r['edges'][0]['before'].update(read_pending=2),
                 lambda r:r['edges'].pop(0),
                 lambda r:r['edges'][0]['before'].update(read_buffer=2**48),
                 lambda r:r['call_rows'][1].__setitem__(7,0),
                 lambda r:r['clocks'][2].__setitem__(3,0),
                 lambda r:r['callbacks'][0].__setitem__(3,0xfff6)]
        with tempfile.TemporaryDirectory()as temporary:
            import json
            path=Path(temporary)/'altered-clock.json'
            for mutate in changes:
                bad=copy.deepcopy(row);mutate(bad);path.write_text(json.dumps(bad))
                with self.assertRaises(ValueError):
                    qualification.validate_clock_group(qualification.load(path),case,markers)

    def test_capture_origin_and_actual_tier_are_not_imported_retirements(self):
        case=cases()[0];source=program(case)[2][0]
        actual=dict(tier='native',window_hits=[dict(source,hits=2)],checkpoint_sha256='a'*64,
            cut=dict(values=[0]*7+[100]),origin_frame=4,prefix_native=20,prefix_interpreted=0)
        capture=dict(schema=1,runtime_abi=ABI,capacity=4096,dropped_instructions=0,
            unreadable_instructions=0,retired_instructions=2,complete=True,
            observations=[dict(source,native_hits=2,interpreted_hits=0)],
            checkpoint_origin=dict(sha256='a'*64,ticks=100,frame=4,native_steps=20,interpreter_steps=0))
        qualification.validate_capture(capture,actual,case,resume=True)
        for change in({'native_steps':22},{'ticks':True},{'sha256':'b'*64},{'frame':5}):
            bad=copy.deepcopy(capture);bad['checkpoint_origin'].update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):
                qualification.validate_capture(bad,actual,case,resume=True)
        bad=copy.deepcopy(capture);bad['observations'][0].update(native_hits=0,interpreted_hits=2)
        with self.assertRaises(ValueError):qualification.validate_capture(bad,actual,case,resume=True)

    def test_written_partial_plan_cannot_claim_the_complete_matrix(self):
        import json
        selected=dict(cases=[cases()[0]['id']],cuts=[0],complete_matrix=False)
        self.assertFalse(qualification.validate_plan(selected)[2])
        full=dict(cases=[case['id']for case in cases()],cuts=[0,1,2],complete_matrix=True)
        self.assertTrue(qualification.validate_plan(full)[2])
        with tempfile.TemporaryDirectory()as temporary:
            path=Path(temporary)/'altered-plan.json'
            for bad in(selected|{'complete_matrix':True},selected|{'cuts':[False]},
                       selected|{'cases':selected['cases']*2},full|{'complete_matrix':False}):
                path.write_text(json.dumps(bad))
                with self.assertRaises(ValueError):qualification.validate_plan(qualification.load(path))

    def test_stale_target_buffer_and_wrong_final_tail_are_refused(self):
        initial=[0]*42;initial[26:30]=[1,0,0xdead,0x6001]
        qualification.validate_prefetch(initial,initial=True)
        pending=initial.copy();pending[26:30]=[1,0,0xa65c,0x6002]
        qualification.validate_prefetch(pending)
        completed=initial.copy();completed[26:30]=[0,0,0x5aa5,0x6003]
        qualification.validate_prefetch(completed)
        for values in(pending,completed):
            bad=values.copy();bad[28]=0xdead
            with self.assertRaises(ValueError):qualification.validate_prefetch(bad)
        bad=completed.copy();bad[29]=0x6002
        with self.assertRaises(ValueError):qualification.validate_prefetch(bad)

    def test_target_requires_actual_hdw_and_two_fetched_sprites(self):
        before=[2,0,0,255,1,0,0,0,1,0,0,1,0,0]
        qualification.validate_target_scope(before,phase())
        qualification.validate_target_scope(before,phase(True))
        for change in({'hstate':0},{'sprite_count':1},{'vstate':0},{'latched_mwr':0},
                       {'sat_pending':1},{'hpos':500},{'burst':1}):
            bad=phase();bad.update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):
                qualification.validate_target_scope(before,bad)

    def test_first_source_bits_are_unique_and_imports_are_not_new_assertions(self):
        qualification.validate_first_causes([4],[3],0)
        qualification.validate_first_causes([4,3],[],1)
        qualification.validate_first_causes([4,3],[],2)
        qualification.validate_first_causes([],[3],0,resume=True)
        qualification.validate_first_causes([],[],1,resume=True)
        qualification.validate_first_causes([],[],2,resume=True)
        for prefix,window,cut,resume in(([4,4],[3],0,False),([4],[3,1],0,False),
                ([],[7],0,False),([4],[3],0,True),([],[3],1,True),([4,3,2],[],2,False)):
            with self.subTest(prefix=prefix,window=window),self.assertRaises(ValueError):
                qualification.validate_first_causes(prefix,window,cut,resume)

if __name__=='__main__':unittest.main()
