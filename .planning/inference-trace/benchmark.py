import json
import statistics
import time
from sage.runtime import LocalEnvironment
from sage.runtime.job_manager import JobManager

def trial():
 env=LocalEnvironment('trace-overhead')
 env.from_batch(range(128)).map(lambda x:x+1).sink(lambda x:None)
 started=time.perf_counter_ns()
 key=env.submit(autostop=True)
 elapsed=time.perf_counter_ns()-started
 JobManager().delete_job(key)
 return elapsed

for _ in range(8): trial()
samples=[trial() for _ in range(60)]
print(json.dumps({'median_ns':statistics.median(samples),'samples_ns':samples}))
