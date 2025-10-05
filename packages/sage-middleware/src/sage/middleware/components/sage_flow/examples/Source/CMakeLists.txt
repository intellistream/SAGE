add_executable(
    generatorT
    generate_vector_records.cpp
)
add_executable(
    fvecs_to_vector_records
    fvecs_to_vector_records.cpp
)
target_link_libraries(generatorT
    candy
)

target_link_libraries(fvecs_to_vector_records
    candy
)