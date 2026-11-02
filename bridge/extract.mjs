import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

export function validateOptions(o) {
  if (!o.input || !o.output || !Number.isFinite(o.maxSeconds) || o.maxSeconds <= 0 || o.maxSeconds > 3600 ||
      !Number.isInteger(o.maxSheets) || o.maxSheets < 1 || o.maxSheets > 200) throw new Error('Invalid extraction options');
}

export async function runExtraction(o, deps) {
  validateOptions(o);
  const {createPipeline,spawnFrames,write} = deps;
  const width=800, height=450, fps=12;
  const p=createPipeline({width,height,fps,queueDepth:0});
  const sheets=[];
  let truncated=false, abort=false, timedOut=false, run;
  function drain() {
    for (let item; (item=p.take());) {
      if (sheets.length >= o.maxSheets) { truncated=true; abort=true; continue; }
      const file='sheet-'+String(sheets.length+1).padStart(4,'0')+'.png';
      write(path.join(o.output,file),item.png);
      sheets.push({file,from:item.from,to:item.to,frames:item.frames});
    }
  }
  run=spawnFrames({source:{kind:'file',path:o.input},width,height,fps,ffmpegPath:o.ffmpeg || 'ffmpeg',onFrame(f) {
    if (abort) return;
    if (f.t >= o.maxSeconds) { truncated=true; abort=true; run?.stop(); return; }
    p.push(f);
    drain();
    if (abort) run?.stop();
  }});
  const timeoutMs=o.timeoutMs ?? 120000;
  if (!Number.isInteger(timeoutMs) || timeoutMs < 1 || timeoutMs > 600000) {
    run.stop();
    throw new Error('Invalid timeout');
  }
  const timer=setTimeout(()=>{ timedOut=true; abort=true; run.stop(); },timeoutMs);
  let result;
  try { result=await run.done; } catch (e) { if (!abort) throw e; result={code:null,frames:0}; }
  finally { clearTimeout(timer); }
  if (timedOut) throw new Error('Video extraction timed out');
  if (!abort && (result.code !== 0 || !result.frames)) throw new Error('FFmpeg failed or produced no frames');
  p.finish();
  drain();
  return {sheets,truncated,stats:p.stats};
}

async function main() {
  const args=process.argv.slice(2), opts={maxSeconds:600,maxSheets:40};
  const keys={'--input':'input','--output':'output','--ffmpeg':'ffmpeg','--max-seconds':'maxSeconds','--max-sheets':'maxSheets','--timeout-ms':'timeoutMs'};
  for (let i=0;i<args.length;i+=2) {
    const k=keys[args[i]];
    if (!k || args[i+1] === undefined) throw new Error('Invalid arguments');
    opts[k]=['maxSeconds','maxSheets','timeoutMs'].includes(k) ? Number(args[i+1]) : args[i+1];
  }
  validateOptions(opts);
  if (!path.isAbsolute(opts.input) || !path.isAbsolute(opts.output)) throw new Error('Input and output must be absolute paths');
  if (!fs.statSync(opts.input).isFile()) throw new Error('Input must be a file');
  if (fs.readdirSync(opts.output).length) throw new Error('Output directory must be empty');
  const {createPipeline}=await import('./vendor/pipeline.js');
  const {spawnFrames}=await import('./vendor/capture.js');
  const result=await runExtraction(opts,{createPipeline,spawnFrames,write:fs.writeFileSync});
  process.stdout.write(JSON.stringify(result)+'\n');
}
if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  main().catch(e=>{process.stderr.write(String(e.message || e)+'\n');process.exitCode=1;});
}
