// Disposable consumer host for an immutable Bots candidate. Receiver metadata
// comes from the actual owned OS process; no synthetic loop acknowledgement.
import {readFile} from 'node:fs/promises';
import {join} from 'node:path';
import {pathToFileURL} from 'node:url';
const [app,configurationPath]=process.argv.slice(2);
const {verifyCandidate}=await import(pathToFileURL(join(app,'scripts/verify-installation-candidate.mjs')).href);
const verified=await verifyCandidate(app);
const {createBotService}=await import(pathToFileURL(join(app,'src/service.mjs')).href);
const {loadWakeHealthConfiguration}=await import(pathToFileURL(join(app,'src/wake-health.mjs')).href);
const config=JSON.parse(await readFile(configurationPath,'utf8')),target=config.targets.fixture;
const native={binding:async()=>{
 try{
  const stat=await readFile(`/proc/${target.process.pid}/stat`,'utf8');
  const birth=stat.slice(stat.lastIndexOf(')')+2).split(' ')[19];
  const boot=(await readFile('/proc/sys/kernel/random/boot_id','utf8')).trim();
  if(boot!==target.process.boot_id)return null;
  return {client_pid:target.process.pid,client_start_time_ticks:birth,pane_id:'owned-pty-receiver'};
 }catch{return null;}
}};
const service=await createBotService({bots:[{id:'fixture',threadId:target.conversation_id}],native,
 controllerHealth:loadWakeHealthConfiguration(configurationPath)});
console.log(JSON.stringify({url:service.url,candidate:verified.identity,sourceRevision:verified.sourceRevision}));
process.once('SIGTERM',async()=>{await service.close();process.exit(0);});
