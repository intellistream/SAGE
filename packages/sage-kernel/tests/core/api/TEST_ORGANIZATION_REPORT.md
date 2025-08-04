# SAGE Core API Test Organization Report
==================================================

## Source-to-Test File Mapping
✅ `src/sage/core/api/base_environment.py` → `tests/core/api/test_base_environment.py`
✅ `src/sage/core/api/local_environment.py` → `tests/core/api/test_local_environment.py`
✅ `src/sage/core/api/remote_environment.py` → `tests/core/api/test_remote_environment.py`
✅ `src/sage/core/api/datastream.py` → `tests/core/api/test_datastream.py`
✅ `src/sage/core/api/connected_streams.py` → `tests/core/api/test_connected_streams.py`

## Test File Structure
### test_base_environment.py
```
class TestBaseEnvironmentInit:
    def test_init_with_defaults()
    def test_init_with_config()
    def test_init_with_empty_config()
class TestBaseEnvironmentConsoleLogLevel:
    def test_set_console_log_level_valid()
    def test_set_console_log_level_case_insensitive()
    def test_set_console_log_level_invalid()
    def test_set_console_log_level_updates_existing_logger()
class TestBaseEnvironmentServiceRegistration:
    def test_register_service_local()
    def test_register_service_remote()
class TestBaseEnvironmentKafkaSource:
    def test_from_kafka_source_basic()
    def test_from_kafka_source_with_options()
class TestBaseEnvironmentDataSources:
    def test_from_source_with_function_class()
    def test_from_source_with_lambda()
    def test_from_collection_with_function_class()
    def test_from_collection_with_lambda()
class TestBaseEnvironmentFromBatch:
    def test_from_batch_with_function_class()
    def test_from_batch_with_list()
    def test_from_batch_with_tuple()
    def test_from_batch_with_range()
    def test_from_batch_with_set()
    def test_from_batch_with_string()
    def test_from_batch_with_invalid_type()
class TestBaseEnvironmentFromFuture:
    def test_from_future()
class TestBaseEnvironmentProperties:
    def test_logger_property_lazy_creation()
    def test_client_property_lazy_creation()
    def test_client_property_with_config()
class TestBaseEnvironmentLoggingSetup:
    def test_setup_logging_system()
class TestBaseEnvironmentAuxiliaryMethods:
    def test_append_method()
    def test_from_batch_collection_internal()
    def test_from_batch_iterable_internal()
    def test_from_batch_iterable_without_len()
class TestBaseEnvironmentEdgeCases:
    def test_empty_config_handling()
    def test_state_exclude_attribute()
    def test_abstract_methods_exist()
class TestBaseEnvironmentIntegration:
    def test_full_pipeline_creation()
    def test_service_registration_workflow()
```

### test_connected_streams.py
```
class TestConnectedStreamsInit:
    def test_init_basic()
    def test_init_single_transformation()
    def test_init_multiple_transformations()
    def test_init_empty_transformations()
class TestConnectedStreamsTransformations:
    def test_map_with_function_class()
    def test_map_with_lambda()
    def test_sink_with_function_class()
    def test_sink_with_lambda()
class TestConnectedStreamsPrint:
    def test_print_with_defaults()
    def test_print_with_custom_params()
class TestConnectedStreamsConnect:
    def test_connect_with_datastream()
    def test_connect_with_connected_streams()
    def test_connect_preserves_order()
class TestConnectedStreamsComap:
    def test_comap_with_function_class()
    def test_comap_with_lambda_functions_raises_error()
    def test_comap_with_lambda_list_raises_error()
    def test_comap_kwargs_warning_with_callables()
    def test_comap_validation_errors()
class TestConnectedStreamsApply:
    def test_apply_method()
class TestConnectedStreamsChaining:
    def test_chaining_transformations()
    def test_chaining_with_sink()
class TestConnectedStreamsMultipleInputs:
    def test_two_input_streams()
    def test_multiple_input_streams()
class TestConnectedStreamsIntegration:
    def test_complex_connection_workflow()
    def test_comap_integration()
class TestConnectedStreamsEdgeCases:
    def test_empty_transformations_operations()
    def test_single_transformation_behavior()
    def test_none_function_handling()
    def test_multiple_operations_on_same_connected_streams()
    def test_transformation_order_preservation()
```

### test_datastream.py
```
class TestDataStreamInit:
    def test_init_basic()
    def test_init_logger_creation()
    def test_init_type_param_resolution()
class TestDataStreamTransformations:
    def test_map_with_function_class()
    def test_map_with_lambda()
    def test_filter_with_function_class()
    def test_filter_with_lambda()
    def test_flatmap_with_function_class()
    def test_flatmap_with_lambda()
    def test_sink_with_function_class()
    def test_sink_with_lambda()
    def test_keyby_with_default_strategy()
    def test_keyby_with_custom_strategy()
    def test_keyby_with_lambda()
class TestDataStreamConnect:
    def test_connect_with_datastream()
    def test_connect_with_connected_streams()
class TestDataStreamFillFuture:
    def test_fill_future_successful()
    def test_fill_future_not_future_stream()
    def test_fill_future_already_filled()
class TestDataStreamPrint:
    def test_print_with_defaults()
    def test_print_with_custom_params()
class TestDataStreamApply:
    def test_apply_method()
class TestDataStreamTypeResolution:
    def test_resolve_type_param_fallback()
    def test_resolve_type_param_with_orig_class()
class TestDataStreamChaining:
    def test_chaining_transformations()
    def test_chaining_with_sink()
class TestDataStreamIntegration:
    def test_complex_pipeline()
    def test_future_stream_workflow()
class TestDataStreamEdgeCases:
    def test_empty_pipeline_operations()
    def test_none_function_handling()
    def test_multiple_sink_operations()
```

### test_from_batch_polymorphism.py
```
```

### test_local_environment.py
```
class TestLocalEnvironmentInit:
    def test_init_with_defaults()
    def test_init_with_custom_name_and_config()
    def test_init_with_none_config()
class TestLocalEnvironmentJobManager:
    def test_jobmanager_property_lazy_creation()
    def test_jobmanager_property_singleton()
class TestLocalEnvironmentSubmit:
    def test_submit_job()
    def test_submit_returns_none()
class TestLocalEnvironmentStop:
    def test_stop_without_env_uuid()
    def test_stop_successful()
    def test_stop_failure_response()
    def test_stop_exception_handling()
class TestLocalEnvironmentClose:
    def test_close_without_env_uuid()
    def test_close_successful()
    def test_close_failure_response()
    def test_close_exception_handling()
class TestLocalEnvironmentGetQd:
    def test_get_qd_default_params()
    def test_get_qd_custom_params()
    def test_get_qd_different_names()
class TestLocalEnvironmentInheritance:
    def test_inherits_from_base_environment()
    def test_platform_is_local()
    def test_inherited_methods_available()
    def test_no_engine_client_in_local()
class TestLocalEnvironmentIntegration:
    def test_full_workflow()
    def test_multiple_queue_descriptors()
class TestLocalEnvironmentEdgeCases:
    def test_stop_close_without_logger()
    def test_multiple_close_calls()
    def test_attributes_exist_after_init()
```

### test_new_remote_env.py
```
```

### test_remote_env_serialization.py
```
```

### test_remote_environment.py
```
class TestRemoteEnvironmentInit:
    def test_init_with_defaults()
    def test_init_with_custom_params()
    def test_init_with_none_config()
    def test_state_exclude_attributes()
class TestRemoteEnvironmentClient:
    def test_client_property_lazy_creation()
    def test_client_property_with_custom_host_port()
class TestRemoteEnvironmentSubmit:
    def test_submit_successful()
    def test_submit_failure_response()
    def test_submit_success_without_uuid()
    def test_submit_serialization_error()
    def test_submit_client_error()
class TestRemoteEnvironmentGetQd:
    def test_get_qd_default_params()
    def test_get_qd_custom_params()
    def test_get_qd_different_names()
class TestRemoteEnvironmentInheritance:
    def test_inherits_from_base_environment()
    def test_platform_is_remote()
    def test_inherited_methods_available()
class TestRemoteEnvironmentLogging:
    def test_init_logging()
    def test_client_creation_logging()
    def test_submit_logging()
class TestRemoteEnvironmentIntegration:
    def test_full_workflow()
    def test_multiple_queue_descriptors()
class TestRemoteEnvironmentEdgeCases:
    def test_config_merging()
    def test_multiple_submit_calls()
    def test_attributes_exist_after_init()
    def test_client_property_thread_safety()
```

### test_remote_environment_server.py
```
```
