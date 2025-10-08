add_executable(
        Streaming_example
        main.cpp
)
add_executable(
        topk
        topk.cpp
)
add_executable(
        itopk
        itopk.cpp
)

add_executable(
        aggregate
        aggregate.cpp
)

target_link_libraries(
        Streaming_example
        candy
)
target_link_libraries(
        topk
        candy
)

target_link_libraries(
        itopk
        candy
)

target_link_libraries(
        aggregate
        candy
)
macro(add_streaming_example name)
        add_executable(${name} ${name}.cpp)
        target_link_libraries(${name} candy)
endmacro()
add_streaming_example(test1)
add_streaming_example(test2)
add_streaming_example(index_perf)
add_streaming_example(buffer_test)