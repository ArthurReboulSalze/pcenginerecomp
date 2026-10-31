"""Original guest programs and finite CPU/stack/device/source IRQ ledgers.

No execution capture supplies expected values. Hardware setup uses guest
stores, real DMA and a complete ten-byte directory command.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
HANDLERS = {4: 0xF800, 2: 0xF840, 1: 0xF880}
ENC = {'sei': 0x78, 'cli': 0x58, 'cld': 0xD8, 'clv': 0xB8,
       'clc': 0x18, 'clx': 0x82, 'cly': 0xC2, 'txs': 0x9A,
       'nop': 0xEA, 'rti': 0x40, 'csh': 0xD4}
LITERAL_COLUMNS = ['pc', 'a', 'x', 'y', 'sp', 'p', 'clock_divisor', 'elapsed_ticks',
    *['mpr'+str(i) for i in range(8)], 'mpr_latch', 'irq_entries', 'irq_vector',
    'rti_steps', 'timer_pending', 'irq_mask', 'timer_enabled', 'timer_counter_wram',
    'irq1_counter_wram', 'irq2_counter_wram', 'irq_requests', 'vdc_status',
    'cd_interrupt_enable', 'cd_interrupt_active', 'cd_ack', 'scsi_signals',
    'scsi_phase', 'scsi_data', 'scsi_response_index', 'vram_dma_pending',
    'pending_vram_read', 'pending_vram_write', 'vdc_wait_ticks']


def encode(op, pc=0):
    name = op[0]
    if name in ENC: return bytes([ENC[name]])
    if name in ('lda', 'ldx', 'tam', 'cmp'):
        return bytes([{'lda': 0xA9, 'ldx': 0xA2, 'tam': 0x53, 'cmp': 0xC9}[name], op[1]])
    if name in ('sta', 'load', 'inc'):
        return bytes([{'sta': 0x8D, 'load': 0xAD, 'inc': 0xEE}[name], op[1]&255, op[1]>>8])
    if name in ('bne', 'bra'):
        return bytes([0xD0 if name == 'bne' else 0x80, (op[1]-pc-2)&255])
    if name == 'tii':
        return bytes([0x73, op[1]&255, op[1]>>8, op[2]&255, op[2]>>8, op[3]&255, op[3]>>8])
    raise ValueError('Unknown authored operation: '+name)


def definitions():
    result = []
    for speed, label in ((12, 'low'), (3, 'high')):
        for mask in range(8):
            result.append(dict(id=f'priority-mask{mask}-{label}', speed=speed, mask=mask, kind='priority'))
        for kind, mask, acc in (
            ('vdc-queued-retain', 5, 1), ('vdc-immediate-cancel', 5, 1),
            ('vdc-rmw-cancel', 5, 1), ('cd-ack-retain', 6, 0xC0),
            ('cd-disable-retain', 6, 0), ('cd-reset-retain', 6, 2),
            ('cd-status-not-ack', 6, 1), ('timer-ack-fallback', 0, 0),
            ('no-auto-ack', 0, 1), ('cd-status-phase', 6, 1),
            ('held-irq1-rti', 5, 1), ('held-irq2-rti', 6, 1)):
            result.append(dict(id=kind+'-'+label, speed=speed, mask=mask, kind=kind, acc=acc))
        result.append(dict(id='priority-wrap-'+label, speed=speed, mask=0, kind='priority', sp=1))
        result.append(dict(id='priority-remap-'+label, speed=speed, mask=0, kind='priority', sp=1, remap=True))
    for case in result:
        case.setdefault('sp', 255); case.setdefault('acc', 1); case.setdefault('remap', False)
        case['queued_accesses'] = case['kind'] != 'vdc-immediate-cancel'
        case['cd_source'] = 0x20 if case['kind'] == 'cd-status-phase' else 0x40
    return result


class Program:
    def __init__(self, pc): self.start = pc; self.code = bytearray(); self.ops = {}
    @property
    def pc(self): return self.start+len(self.code)
    def add(self, *op):
        pc = self.pc; self.ops[pc] = op; self.code.extend(encode(op, pc)); return pc
    def delay(self, length): self.add('tii', 0x2200, 0x2200, length)
    def register(self, number, value):
        for address, byte in ((0, number), (2, value&255), (3, value>>8)):
            self.add('lda', byte); self.add('sta', address)


def source(pc, mapping, op):
    raw = list(encode(op, pc))
    return dict(pc=pc, mpr=list(mapping), data=raw,
        physical=[(mapping[((pc+i)&65535)>>13]<<13)|((pc+i)&8191) for i in range(len(raw))])


def make_program(case):
    p = Program(0xE000)
    for op in [('sei',), ('lda', 0), ('tam', 0xFD), ('lda', 248), ('tam', 2),
               ('lda', 0), ('sta', 0x2000), ('tii', 0x2000, 0x2001, 8191),
               ('lda', 255), ('tam', 1)]: p.add(*op)
    if case['speed'] == 3: p.add('csh')
    p.add('lda', 7); p.add('sta', 0x1402)
    p.add('lda', 0); p.add('sta', 0x1802); p.add('sta', 0x1800); p.delay(5000)
    for byte in [0xDE]+[0]*9:
        p.add('lda', byte); p.add('sta', 0x1801)
        p.add('lda', 0x80); p.add('sta', 0x1802)
        p.add('lda', 0); p.add('sta', 0x1802); p.delay(200)
    p.delay(1000)
    if case['kind'] == 'cd-status-phase':
        for _ in range(4):
            p.add('lda', 0xC0); p.add('sta', 0x1802)
            p.add('lda', 0x40); p.add('sta', 0x1802); p.delay(1100)
    p.add('lda', case['cd_source']); p.add('sta', 0x1802)
    # One real VRAM DMA supplies IRQ1; CR zero prevents later raster IRQs.
    for number, value in ((15, 2), (16, 0), (17, 1), (18, 0)): p.register(number, value)
    p.delay(200)
    for op in [('lda', 0), ('sta', 0x0C00), ('lda', 1), ('sta', 0x0C01)]: p.add(*op)
    p.delay(1000)
    p.add('lda', 0); p.add('sta', 0x0C01)
    # TII saves Y/A/X on the real stack: clear all three save bytes afterwards.
    for address in (0x2100, 0x21FF, 0x21FE): p.add('sta', address)
    p.add('lda', case['mask']); p.add('sta', 0x1402)
    if case['remap']: p.add('lda', 1); p.add('tam', 128)
    for op in [('ldx', case['sp']), ('txs',), ('clx',), ('cly',), ('cld',), ('clv',), ('clc',), ('lda', case['acc'])]: p.add(*op)
    marker = p.pc; primer = list(p.ops.items())
    p.add('cli')
    special = {'vdc-queued-retain': ('load', 0), 'vdc-immediate-cancel': ('load', 0),
               'vdc-rmw-cancel': ('inc', 0), 'cd-ack-retain': ('sta', 0x1802),
               'cd-disable-retain': ('sta', 0x1802), 'cd-reset-retain': ('sta', 0x1804),
               'cd-status-not-ack': ('load', 0x1803), 'timer-ack-fallback': ('sta', 0x1403)}
    p.add(*special.get(case['kind'], ('nop',)))
    for _ in range(4): p.add('nop')
    terminal = p.pc; p.add('bra', terminal)
    if p.pc >= 0xF800: raise ValueError('Authored main overlaps handler space')
    programs = dict(p.ops); segments = [(p.start, bytes(p.code))]
    for bit, target in HANDLERS.items():
        for remapped in (False, True):
            h = Program(target+(0x100 if remapped else 0)); cell = 0x2010+{4:0, 2:1, 1:2}[bit]
            held = case['kind'] == ('held-irq1-rti' if bit == 2 else 'held-irq2-rti' if bit == 1 else '')
            if case['kind'] == 'no-auto-ack': h.add('nop')
            if held:
                h.add('inc', cell); h.add('load', cell); h.add('cmp', 2); branch = h.add('bne', 0)
            if bit == 4: h.add('lda', 0); h.add('sta', 0x1403)
            elif bit == 2: h.add('load', 0)
            else:
                h.add('lda', 0x80|case['cd_source']); h.add('sta', 0x1802)
                h.add('lda', 0x80); h.add('sta', 0x1802)
            if not held: h.add('inc', cell)
            if held:
                h.ops[branch] = ('bne', h.pc)
                offset = branch-h.start; h.code[offset:offset+2] = encode(h.ops[branch], branch)
            h.add('rti'); programs.update(h.ops); segments.append((h.start, bytes(h.code)))
    rom = bytearray([0xEA]*262144)
    for address, raw in segments: rom[address&8191:(address&8191)+len(raw)] = raw
    for bit, vector in ((1, 0xFFF6), (2, 0xFFF8), (4, 0xFFFA)):
        rom[vector&8191:(vector&8191)+2] = HANDLERS[bit].to_bytes(2, 'little')
    rom[8190:8192] = p.start.to_bytes(2, 'little'); rom[8192:16384] = rom[:8192]
    for bit, vector in ((1, 0xFFF6), (2, 0xFFF8), (4, 0xFFFA)):
        rom[8192+(vector&8191):8192+(vector&8191)+2] = (HANDLERS[bit]+0x100).to_bytes(2, 'little')
    mapping = [0]*8; a = 0; primer_sources = []
    for pc, op in primer:
        primer_sources.append(source(pc, mapping, op))
        if op[0] == 'lda': a = op[1]
        elif op[0] == 'tam':
            for page in range(8):
                if op[1]&(1<<page): mapping[page] = a
    return bytes(rom), programs, primer_sources, marker, terminal, mapping


def literals(case, program, marker, mapping, profile):
    """Only the finite authored operation set; no runtime/decoder dependency."""
    ram = bytearray(8192); pc = marker; a = case['acc']; x = y = 0; sp = case['sp']
    p = 4|(a&128)|(2 if a == 0 else 0); ticks = entries = vector = rti = 0
    pending = True; mask = case['mask']; vs = 0x10; cd_enable = cd_active = case['cd_source']
    ack = reset = False; phase = 7 if case['kind'] == 'cd-status-phase' else 4
    signals = 0xD8 if phase == 7 else 0xC8; data = 0 if phase == 7 else 1; offset = 0 if phase == 7 else 1
    mpr = list(mapping); latch = 1 if case['remap'] else 255; rows = []; sources = []
    def requests(): return (4 if pending else 0)|(2 if vs else 0)|(1 if cd_enable&cd_active else 0)
    def push(value):
        nonlocal sp
        ram[0x100+sp] = value&255; sp = (sp-1)&255
    def pop():
        nonlocal sp
        sp = (sp+1)&255; return ram[0x100+sp]
    def nz(value):
        nonlocal p
        p = (p&~130)|(value&128)|(2 if value == 0 else 0)
    def row(ordinal, delivered=0, return_pc=None, fixed_wait_count=0):
        digest = hashlib.sha256(ram).hexdigest()
        values = [pc,a,x,y,sp,p,case['speed'],ticks,*mpr,latch,entries,vector,rti,int(pending),mask,0,
                  ram[0x10],ram[0x11],ram[0x12],requests(),vs,cd_enable,cd_active,int(ack),signals,
                  phase,data,offset,0,0,0,0]
        assert len(values) == 39
        state = dict(pc=pc,a=a,x=x,y=y,sp=sp,p=p,mpr=list(mpr),mpr_latch=latch,
            physical_pc=(mpr[pc>>13]<<13)|(pc&8191),clock_divisor=case['speed'],ticks=ticks,wram_sha256=digest)
        return dict(ordinal=ordinal,values=values,state=state,wram_sha256=digest,
                    irq_count=int(bool(delivered)),irq_vector=delivered or None,
                    irq_return_pc=return_pc,fixed_wait_count=fixed_wait_count,
                    internal_clocked_ticks=fixed_wait_count*case['speed'])
    initial = row(0)
    for ordinal in range(1,49):
        op = program[pc]; name = op[0]; raw = encode(op, pc); sources.append(source(pc,mpr,op))
        sampled = 0 if p&4 else requests()&~mask
        pc = (pc+len(raw))&65535; cycles = 2; fixed_wait_count = 0
        if name == 'lda': a = op[1]; nz(a)
        elif name == 'cli': p &= ~4
        elif name == 'load':
            cycles = 5; address = op[1]
            if address == 0:
                a = vs; vs = 0; cycles += 1; fixed_wait_count = 1
                if profile == 'runtime' and not case['queued_accesses']: sampled = 0 if p&4 else requests()&~mask
            elif address == 0x1803: a = cd_active|0x12
            elif 0x2000 <= address < 0x4000: a = ram[address&8191]
            else: raise ValueError('Unauthored read')
            nz(a)
        elif name == 'inc':
            address = op[1]; cycles = 7
            if address == 0:
                vs = 0; cycles += 2; fixed_wait_count = 2
                sampled = 0 if p&4 else requests()&~mask; nz(0x11)
            else:
                at = address&8191; ram[at] = (ram[at]+1)&255; nz(ram[at])
        elif name == 'sta':
            address = op[1]; cycles = 5
            if address == 0x1403: pending = False
            elif address == 0x1802:
                cd_enable = a&127
                if reset:
                    ack = False; signals = 0x100; phase = data = offset = cd_active = 0
                else:
                    ack = bool(a&128)
                    if ack: signals = (signals|2)&~0x40; cd_active = 0
                    else: signals &= ~2
            elif address == 0x1804:
                reset = bool(a&2)
                if reset: ack = False; signals = 0x100; phase = data = offset = cd_active = 0
            else: raise ValueError('Unauthored store')
        elif name == 'cmp':
            result = (a-op[1])&255; p = (p&~1)|int(a>=op[1]); nz(result)
        elif name == 'bne':
            if not p&2: pc = op[1]; cycles = 4
        elif name == 'bra': pc = op[1]; cycles = 4
        elif name == 'rti':
            p = pop()&~16; low = pop(); pc = low|(pop()<<8); cycles = 7; rti += 1
        elif name != 'nop': raise ValueError('Unauthored measured operation')
        p &= ~32; ticks += cycles*case['speed']
        eligible = sampled & (3|(4 if pending else 0))
        bit = 4 if eligible&4 else 2 if eligible&2 else 1 if eligible&1 else 0
        delivered = {4:0xFFFA,2:0xFFF8,1:0xFFF6,0:0}[bit]
        return_pc = pc if bit else None
        if bit:
            push(pc>>8); push(pc); push(p&~16); p = (p|4)&~40
            pc = HANDLERS[bit]+(0x100 if case['remap'] else 0); entries += 1; vector = delivered
            ticks += 8*case['speed']
        rows.append(row(ordinal,delivered,return_pc,fixed_wait_count))
    return initial, rows, sources


def authored_fixture():
    cases = []; images = {}; all_sources = {}
    for definition in definitions():
        case = dict(definition); rom, program, primer, marker, terminal, mapping = make_program(case)
        case.update(rom=case['id']+'.pce',entry=0xE000,marker=marker,end_pc=terminal,
                    primer_steps=len(primer),steps=48,initial_mpr=[0]*8,measured_mpr=mapping,
                    block_steps=sum(row['data'][0] == 0x73 for row in primer))
        for profile in ('runtime','gear'):
            initial, rows, measured = literals(case,program,marker,mapping,profile)
            case['expected_initial_'+profile] = initial; case['expected_'+profile] = rows
            counts = Counter(); records = {}
            for item in primer+measured:
                assert [rom[i] for i in item['physical']] == item['data']
                key = (item['pc'],tuple(item['mpr']),tuple(item['data']))
                counts[key] += 1; records[key] = item
            ledger = [dict(records[key],hits=counts[key]) for key in sorted(counts)]
            case['source_hits_'+profile] = ledger
            for item in ledger:
                key = (item['pc'],tuple(item['mpr']),tuple(item['data']))
                all_sources[key] = dict(item,native_hits=0,interpreted_hits=1)
        case['initial'] = case['expected_initial_runtime']; case['source_hits'] = case['source_hits_runtime']
        case['rom_sha256'] = hashlib.sha256(rom).hexdigest(); cases.append(case); images[case['id']] = rom
    return cases, images, list(all_sources.values())


def generate(out,emit_module=True):
    from pcerecomp.abi import ABI
    out = Path(out); out.mkdir(parents=True,exist_ok=True); cases,images,sources = authored_fixture()
    media = bytes(16*2048); (out/'authored.bin').write_bytes(media)
    (out/'authored.cue').write_text('FILE "authored.bin" BINARY\n  TRACK 01 MODE1/2048\n    INDEX 01 00:00:00\n',encoding='ascii')
    for case in cases: (out/case['rom']).write_bytes(images[case['id']])
    if emit_module:
        from pcerecomp.emitter import emit_capture
        observations = [{key:value for key,value in item.items() if key != 'hits'} for item in sources]
        capture = dict(schema=1,runtime_abi=ABI,capacity=len(observations),dropped_instructions=0,
            unreadable_instructions=0,retired_instructions=len(observations),complete=True,observations=observations)
        with TemporaryDirectory(prefix='irq-device-authored-',dir=out) as stage:
            target=Path(stage)/'module'; emit_capture(capture,target,single_unit=True)
            for path in target.iterdir(): (out/path.name).write_bytes(path.read_bytes())
    header=['#pragma once','#include <array>','#include <cstdint>','#include <string>','#include <stdexcept>','#include <vector>',
        'struct IrqDeviceLiteral { std::array<std::uint64_t,39> values; const char* wram_sha256; unsigned irq_count,irq_vector; };',
        'struct IrqDeviceCase { const char* id; const char* rom; unsigned entry,primer_steps,steps,marker,end_pc; IrqDeviceLiteral initial; const IrqDeviceLiteral* runtime_rows; const IrqDeviceLiteral* gear_rows; bool queued_accesses; unsigned block_steps; };']
    def literal(row):return '{{'+','.join(map(str,row['values']))+'},"'+row['wram_sha256']+'",'+str(row['irq_count'])+','+str(row['irq_vector'] or 0)+'}'
    for index,case in enumerate(cases):
        for profile in ('runtime','gear'):
            header.append(f'inline constexpr IrqDeviceLiteral irq_device_{index}_{profile}[]'+'{'+','.join(literal(row)for row in case['expected_'+profile])+'};')
    header.append('inline constexpr IrqDeviceCase irq_device_cases[]{')
    for index,case in enumerate(cases):
        header.append('{"'+case['id']+'","'+case['rom']+'",'+','.join(str(case[key])for key in ('entry','primer_steps','steps','marker','end_pc'))+','+literal(case['initial'])+f',irq_device_{index}_runtime,irq_device_{index}_gear,'+str(case['queued_accesses']).lower()+','+str(case['block_steps'])+'},')
    header.extend(['};','inline const IrqDeviceCase& irq_device_case(const std::string& name){for(const auto& item:irq_device_cases)if(name==item.id)return item;throw std::runtime_error("Unknown authored IRQ device case");}',
                   'inline std::vector<std::uint8_t> irq_device_rom(const IrqDeviceCase& item){std::vector<std::uint8_t> rom(262144,0xEA);'])
    for case in cases:
        raw=images[case['id']]; changed=[(i,v)for i,v in enumerate(raw)if v!=0xEA]
        header.append('if(std::string(item.id)=="'+case['id']+'"){'+''.join(f'rom[{i}]={v};'for i,v in changed)+'return rom;}')
    header.append('throw std::runtime_error("Unknown authored BIOS");}')
    (out/'irq_device_fixture.hpp').write_text('\n'.join(header),encoding='utf-8')
    result=dict(schema=1,runtime_abi=ABI,cases=cases,cue='authored.cue',literal_columns=LITERAL_COLUMNS,
        media_files=[dict(path=name,sha256=hashlib.sha256((out/name).read_bytes()).hexdigest(),bytes=(out/name).stat().st_size)for name in ('authored.cue','authored.bin')],
        source_plan='Authored finite instruction ledger; no runtime capture supplied expectations.',
        transport_end='Handlers consume the current requested byte and mask IRQ2 with ACK held. This is not an idle/completed-command claim.')
    (out/'fixture.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8'); return result


if __name__ == '__main__': generate(sys.argv[1])
