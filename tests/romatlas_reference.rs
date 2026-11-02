// Authored isolated adapter. original_decode is the unmodified private GPL
// RomAtlas module, and huc6280_emu is its original pinned dependency. Neither
// is linked to the toolkit. No image/frontend, firmware or retail data is used.
use serde::Deserialize;
use serde_json::json;
use std::{collections::BTreeMap, io::{self, BufRead}};
use huc6280_emu::{Huc6280, Registers, Flags};
use huc6280_emu::bus::{BusInterface, InterruptLines, ClockSpeed};

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Request { id:u32, pc:u32, bytes:Vec<u8>, mpr:[u8;8], phase:String }
fn mapped(pc:u32,mpr:&[u8;8])->u32 {u32::from(mpr[((pc&65535)>>13)as usize])*8192+(pc&8191)}
struct Bus {memory:BTreeMap<u32,u8>, reads:Vec<(u32,u8)>, writes:Vec<(u32,u8)>, operations:usize}
impl Bus {fn bound(&mut self){self.operations+=1;assert!(self.operations<=64,"authored CPU operation bound");}}
impl BusInterface for Bus {
    fn read(&mut self,address:u32)->u8 {self.bound();let value=*self.memory.get(&address).expect("unauthored physical read");self.reads.push((address,value));value}
    fn write(&mut self,address:u32,value:u8){self.bound();self.writes.push((address,value));}
    fn idle(&mut self){self.bound();}
    fn interrupt_lines(&self)->InterruptLines {InterruptLines::default()}
    fn set_clock_speed(&mut self,_:ClockSpeed){panic!("speed change outside authored probe");}
}
fn run(r:Request)->anyhow::Result<serde_json::Value> {
    anyhow::ensure!(r.bytes.len()<=7,"authored byte bound");
    if r.phase=="decode" {
        let context=original_decode::Context{mpr:r.mpr.map(Some),sf2_bank:None};
        return Ok(match original_decode::decode(original_decode::Cpu::Main,&r.bytes,r.pc,context) {
            Ok(instruction)=>json!({"id":r.id,"ok":true,"instruction":instruction}),
            Err(error)=>json!({"id":r.id,"ok":false,"error":error.to_string()}),
        });
    }
    anyhow::ensure!(r.phase=="cpu"&&r.pc<=65535&&!r.bytes.is_empty(),"authored CPU recipe");
    let length=match r.bytes[0] {0xea=>1,0xa9=>2,0x4c=>3,0x00=>2,_=>anyhow::bail!("CPU opcode outside explicit authored set")};
    anyhow::ensure!(r.bytes.len()>=length,"truncated authored CPU instruction");
    let mut bus=Bus{memory:BTreeMap::new(),reads:Vec::new(),writes:Vec::new(),operations:0};
    for (n,value)in r.bytes.iter().enumerate(){bus.memory.insert(mapped(r.pc+n as u32,&r.mpr),*value);}
    if r.bytes[0]==0 {bus.memory.insert(mapped(0xfff6,&r.mpr),0x67);bus.memory.insert(mapped(0xfff7,&r.mpr),0x45);}
    let mut cpu=Huc6280::new();
    cpu.set_registers(Registers{a:0,x:0,y:0,pc:r.pc as u16,s:0xff,p:Flags::from(4),mpr:r.mpr});
    cpu.execute_instruction(&mut bus);
    Ok(json!({"id":r.id,"ok":true,"cpu":{"pc":cpu.registers().pc,"a":cpu.registers().a,"s":cpu.registers().s,
              "reads":bus.reads,"writes":bus.writes,"operations":bus.operations}}))
}
fn main()->anyhow::Result<()> {
    for (n,line)in io::stdin().lock().lines().enumerate(){
        anyhow::ensure!(n<65536,"authored record bound");let line=line?;
        anyhow::ensure!(line.len()<=2048,"authored request size bound");
        let request:Request=serde_json::from_str(&line)?;
        println!("{}",run(request)?);
    }
    Ok(())
}
