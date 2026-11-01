"""Pure admission of retained CD timing observations; never drives a guest."""
from scripts.cd_timing_reference import cases,seek_ticks

def require(ok,why):
    if not ok:raise ValueError(why)

def integer(value):
    require(type(value)is int and 0<=value<2**64,'Exact bounded timing integer required');return value

def split_rows(rows):
    require(type(rows)is list,'Timing rows must be an array');result={};current=None
    for row in rows:
        require(type(row)is dict and type(row.get('kind'))is str,'Typed timing record required')
        if row['kind']=='case':
            require(set(row)=={'kind','id','profile'}and row['id']not in result,'Unique authored timing case required');current=[];result[row['id']]=(row['profile'],current)
        else:require(current is not None,'Timing observation before case');current.append(row)
    require(list(result)==[v['id']for v in cases()],'Exact authored case sequence required');return result

def validate_admission(admission,state,profile):
    require(set(admission)=={'kind','op','mode','lba','count','head_before','ack_entry','after'},'Exact admission fields required')
    for key in set(admission)-{'kind'}:integer(admission[key])
    require(admission['ack_entry']<=admission['after']==state['ticks'],'Actual final ACK admission window required')
    op=admission['op'];lo,hi=admission['ack_entry'],admission['after'];target=admission['lba'];head=admission['head_before']
    duration=3221590 if profile=='fixed'else seek_ticks(head,target)
    def event(field,delay):require(lo+delay<=state[field]<=hi+delay,'Command deadline outside actual ACK window: '+field)
    if op==8 and target<14000:
        event('load',duration+286363);require(state['seek']==state['play']==0 and state['logical'][0]==1,'READ must cancel audio timelines');require(state['logical'][6]==head,'READ issue moved retained head')
    elif op==0xD8:
        split=profile=='gear-distance'and duration>4810909;event('seek',duration-4810909 if split else duration)
        if split and admission['mode']:event('play',duration);require(state['play']-state['seek']==4810909,'Seek/playback split must be exactly224ms')
        else:require(state['play']==0,'Unsplit/paused D8 invented playback latency')
        require(state['logical'][0]==(0 if admission['mode']else 2)and state['logical'][1:4]==[target,target,13999]and state['logical'][6]==target,'Accepted D8 target/head/state differs')
    elif op==0xD9 and admission['mode']==3:
        if state['seek']:require(state['play']-state['seek']==4810909,'Resume must follow retained seek plus224ms')
        else:event('play',4810909)
    elif op in(0xDA,0xD9):require(state['play']==0,'Pause/stop retained playback deadline')

def validate_reset(bylabel,tier):
    require(set(bylabel)>={'seeking','reset','later'},'Complete reset source points required')
    seeking,reset,later=(bylabel[k]for k in('seeking','reset','later'))
    require(seeking['seek']>reset['ticks']and seeking['play']>seeking['seek'],'Actual pending split seek before reset required')
    expected=list(seeking['logical']);expected[0]=3;expected[6]=0
    require(reset['logical']==expected,'Reset must preserve every other stopped-audio/head tuple field')
    final=list(expected)
    if tier=='gear':final[4]=final[2] # Original completed seek latches its target as subcode origin.
    require(later['logical']==final,'Exact later original/tool reset audio tuple differs')
    for state in(reset,later):require(state['play']==state['load']==0 and state['logical'][6]==0 and state['phase']==state['signals']==0,'Reset playback/load/head/bus cancellation differs')
    if tier=='gear':require(reset['seek']==seeking['seek'],'Original Gear reset must retain the exact pending seek')
    else:require(reset['seek']==0,'Toolkit reset must retain its established strong seek cancellation')
    require(later['seek']==0,'Retained original seek must naturally expire by later observation')

def validate_initial_error(states,tier):
    expected=[3 if tier=='gear'else 1]+[0]*10
    require(all(state['logical']==expected and state['seek']==state['play']==state['load']==0 for state in states),'Invalid initial READ must preserve each engine original reset audio/head/deadline state')

def validate_latch(point):
    require(set(point)=={'kind','label','ticks','strobe_ticks','interval_ticks','value'},'Exact latch strobe/read observation fields')
    for key in('ticks','strobe_ticks','interval_ticks','value'):integer(point[key])
    require(point['interval_ticks']>=700 and point['ticks']>point['strobe_ticks'],'Actual latch strobe interval/read order differs')
    require(point['value']==0 if point['label']=='before-playback'else point['value']in(0x1234,0xedcc),'Actual source DAC did not preserve silent/new playback gate')

def validate_one(rows,tier):
    groups=split_rows(rows);checks=0
    for definition in cases():
        profile,items=groups[definition['id']];require(profile==definition['profile'],'Case profile differs')
        expected_labels=[s.split()[1]for s in definition['steps']if s.startswith('P ')];states=[v for v in items if v['kind']=='state'];require([v['label']for v in states]==expected_labels,'Exact checkpoint/deadline observation labels required')
        for state in states:
            require(set(state)=={'kind','label','ticks','phase','signals','seek','play','load','logical'},'Exact timing state fields')
            for key in('ticks','phase','signals','seek','play','load'):integer(state[key])
            require(type(state['logical'])is list and len(state['logical'])==11,'Complete drive logical tuple')
            for value in state['logical']:integer(value)
        require(all(a['ticks']<=b['ticks']for a,b in zip(states,states[1:])),'Within-case clocks regressed')
        admissions=[v for v in items if v['kind']=='admission'];replies=[v for v in items if v['kind']=='reply'];cps=[v for v in items if v['kind']=='checkpoint']
        latches=[v for v in items if v['kind']=='latch'];require([v['label']for v in latches]==[s.split()[1]for s in definition['steps']if s.startswith('L ')],'Every authored CDDA latch read must be retained')
        for point in latches:validate_latch(point)
        require(all(b['strobe_ticks']-a['strobe_ticks']==b['interval_ticks']for a,b in zip(latches,latches[1:])),'Actual consecutive latch strobe interval differs')
        require(len(admissions)==sum(s.startswith('S ')for s in definition['steps'])and len(replies)==sum(s.startswith('D ')for s in definition['steps'])and len(cps)==definition['steps'].count('K'),'Every authored operation needs retained evidence')
        for point in cps:require(set(point)=={'kind','whole_core_roundtrip'}and point['whole_core_roundtrip']is(tier!='gear'),'Explicit original/tool checkpoint scope differs')
        for reply in replies:
            require(set(reply)=={'kind','status','message','bytes','sum','data'},'Exact raw reply fields')
            for k in('status','message','bytes','sum'):integer(reply[k])
            require(type(reply['data'])is list and len(reply['data'])==reply['bytes']and sum(reply['data'])==reply['sum']and all(type(v)is int and 0<=v<=255 for v in reply['data']),'Actual payload extent/checksum/type differs')
            expected=2 if definition['id']=='read-past-leadout'and tier!='gear'else 0
            require(reply['status']==reply['message']==expected,'Known command completion status/message differs')
        for index,item in enumerate(items[:-1]):
            if item['kind']=='admission'and items[index+1]['kind']=='state'and items[index+1]['ticks']==item['after']:
                validate_admission(item,items[index+1],'gear-distance'if tier=='gear'else profile);checks+=1
        bylabel={v['label']:v for v in states}
        if 'before-load'in bylabel:
            a,b=bylabel['before-load'],bylabel['at-load'];require(a['load']==a['ticks']+1 and a['logical'][6]==admissions[-1]['head_before'],'Pre-load edge advanced head early');require(b['logical'][6]==min(admissions[-1]['lba']+1,13999),'Successful load did not advance head')
        if 'before-seek'in bylabel:require(bylabel['before-seek']['seek']==bylabel['before-seek']['ticks']+1 and bylabel['at-seek']['seek']==0,'Seek completion edge differs')
        if 'before-play'in bylabel:require(bylabel['before-play']['play']==bylabel['before-play']['ticks']+1 and bylabel['at-play']['play']==0,'Playback completion edge differs')
        if definition['id']=='reset-during-seek':
            validate_reset(bylabel,tier)
        if definition['id']=='read-past-leadout':
            validate_initial_error(states,tier)
        if definition['id']=='read-during-seek':require(admissions[-1]['head_before']==7000,'READ during seek must use immediately changed target head')
        if definition['id']=='q-during-seek':require(replies[-1]['data']==[2,65,1,1,0,0,0,0,2,0],'DD during seek must retain old head')
        if definition['id']=='q-during-play-delay':require(replies[-1]['data']==[0,1,2,1,0,0,0,1,53,37],'DD during playback latency must report target')
    return checks

def qualify(outputs):
    require(set(outputs)=={f's{s}-{tier}'for s in(3,12)for tier in('gear','native','interpreter')},'Complete original/native/interpreter speed matrix required');summary=[];raw_differences=[]
    for speed in(3,12):
        rows={tier:outputs[f's{speed}-{tier}']['rows']for tier in('gear','native','interpreter')}
        for tier in rows:validate_one(rows[tier],tier)
        require(rows['native']==rows['interpreter'],'Native/interpreter timing observations differ')
        g,n=split_rows(rows['gear']),split_rows(rows['native'])
        for definition in cases():
            _,gg=g[definition['id']];_,nn=n[definition['id']]
            if definition['profile']=='fixed':continue
            gs=[v for v in gg if v['kind']=='state'];ns=[v for v in nn if v['kind']=='state']
            require([(v['label'],v['value'])for v in gg if v['kind']=='latch']==[(v['label'],v['value'])for v in nn if v['kind']=='latch'],'Original/tool DAC latch values differ')
            for a,b in zip(gs,ns):
                indices=(1,2,3,5,6)if definition['id']=='read-past-leadout'else(0,1,2,3,5,6)
                require([a['logical'][i]for i in indices]==[b['logical'][i]for i in indices],'Original drive/head state differs: '+definition['id']+'/'+a['label'])
                if (a['phase'],a['signals'])!=(b['phase'],b['signals']):raw_differences.append(dict(case=definition['id'],label=a['label'],divisor=speed,gear=[a['phase'],a['signals']],tool=[b['phase'],b['signals']]))
        summary.append(dict(divisor=speed,cases=len(cases()),native=outputs[f's{speed}-native']['work']['calls'],interpreted=outputs[f's{speed}-interpreter']['work']['calls']))
    return dict(passed=True,scope='Selected supervised command/head/deadline and encoded guest-port state, not cross-core CPU phase or hardware proof.',speeds=summary,raw_phase_differences=raw_differences,
                reference_policy_differences=[dict(case='reset-during-seek',gear='Exact pending seek retained; playback/load canceled and head0; seek naturally expires.',tool='Established strong seek/playback/load cancellation and head0.'),dict(case='read-past-leadout',gear='GOOD status/message0; full original reset STOPPED3 audio tuple retained.',tool='CHECK CONDITION status/message2; full explicit sandbox IDLE1 audio tuple retained; existing sense policy unchanged.')],
                fixed_controls='Original Gear always uses its distance model; fixed plan controls independently verify toolkit legacy literal timing.')
