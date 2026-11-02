import { test } from 'node:test';
import assert from 'node:assert/strict';
import { validateOptions, runExtraction } from '../extract.mjs';

test('rejects unsafe limits', () => {
  assert.throws(() => validateOptions({input:'x',output:'y',maxSeconds:0,maxSheets:4}));
  assert.throws(() => validateOptions({input:'x',output:'y',maxSeconds:10,maxSheets:0}));
});

test('drains completed sheets and preserves final frames', async () => {
  const written=[]; let queued=[]; let stopped=false;
  const p={push(f){if(f.t===1) queued.push({png:Buffer.from('a'),from:0,to:1,frames:[{t:1}]})},take(){return queued.shift()},finish(){queued.push({png:Buffer.from('b'),from:2,to:2,frames:[{t:2}]})},stats:{kept:2}};
  const capture=({onFrame})=>({stop(){stopped=true},done:Promise.resolve().then(()=>{onFrame({t:1});onFrame({t:2});return {code:0,frames:2}})});
  const r=await runExtraction({input:'x',output:'y',maxSeconds:10,maxSheets:4},{createPipeline:()=>p,spawnFrames:capture,write:(path,data)=>written.push([path,data])});
  assert.equal(r.sheets.length,2); assert.equal(written.length,2); assert.equal(stopped,false); assert.equal(r.truncated,false);
});

test('reports duration truncation without treating the stopped process as an error', async () => {
  let stopped=false;
  const p={push(){},take(){return null},finish(){},stats:{}};
  const capture=({onFrame})=>({stop(){stopped=true},done:Promise.resolve().then(()=>{onFrame({t:2});throw new Error('killed')})});
  const r=await runExtraction({input:'x',output:'y',maxSeconds:1,maxSheets:4},{createPipeline:()=>p,spawnFrames:capture,write:()=>{}});
  assert.equal(r.truncated,true); assert.equal(stopped,true);
});

test('rejects a failed ffmpeg even if it wrote no diagnostic', async () => {
  const p={push(){},take(){return null},finish(){},stats:{}};
  await assert.rejects(runExtraction({input:'x',output:'y',maxSeconds:1,maxSheets:4},{createPipeline:()=>p,spawnFrames:()=>({stop(){},done:Promise.resolve({code:1,frames:0})}),write:()=>{}}), /FFmpeg failed/);
});

test('times out and explicitly stops the ffmpeg child', async () => {
  let stopped=false, resolveDone;
  const p={push(){},take(){return null},finish(){},stats:{}};
  const capture=()=>({stop(){stopped=true;resolveDone({code:null,frames:0})},done:new Promise(resolve=>{resolveDone=resolve})});
  await assert.rejects(runExtraction({input:'x',output:'y',maxSeconds:1,maxSheets:4,timeoutMs:10},{createPipeline:()=>p,spawnFrames:capture,write:()=>{}}),/timed out/);
  assert.equal(stopped,true);
});
