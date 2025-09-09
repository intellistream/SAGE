from sage.core.builder.pipeline_decorator import pipeline

@pipeline(namespace = 'local')
def ppl(input_stream):
    result_stream = input_stream.map(lambda x:x*2)
    return result_stream

print(ppl(10))