# SAGE Core API Test Coverage Report
==================================================

**Total Test Files**: 9
**Total Test Classes**: 49
**Total Test Methods**: 150

## test_connected_streams.py
- **Test Classes**: 10
- **Test Methods**: 30
- **Markers Used**: integration, unit
- **Lines of Code**: 537
- **Description**: Tests for sage

  ### TestConnectedStreamsInit (4 tests)
  - `test_init_basic` [pytest.mark.unit]
  - `test_init_single_transformation` [pytest.mark.unit]
  - `test_init_multiple_transformations` [pytest.mark.unit]
  - `test_init_empty_transformations` [pytest.mark.unit]

  ### TestConnectedStreamsTransformations (4 tests)
  - `test_map_with_function_class` [pytest.mark.unit]
  - `test_map_with_lambda` [pytest.mark.unit]
  - `test_sink_with_function_class` [pytest.mark.unit]
  - `test_sink_with_lambda` [pytest.mark.unit]

  ### TestConnectedStreamsPrint (2 tests)
  - `test_print_with_defaults` [pytest.mark.unit]
  - `test_print_with_custom_params` [pytest.mark.unit]

  ### TestConnectedStreamsConnect (3 tests)
  - `test_connect_with_datastream` [pytest.mark.unit]
  - `test_connect_with_connected_streams` [pytest.mark.unit]
  - `test_connect_preserves_order` [pytest.mark.unit]

  ### TestConnectedStreamsComap (5 tests)
  - `test_comap_with_function_class` [pytest.mark.unit]
  - `test_comap_with_lambda_functions_raises_error` [pytest.mark.unit]
  - `test_comap_with_lambda_list_raises_error` [pytest.mark.unit]
  - `test_comap_kwargs_warning_with_callables` [pytest.mark.unit]
  - `test_comap_validation_errors` [pytest.mark.unit]

  ### TestConnectedStreamsApply (1 tests)
  - `test_apply_method` [pytest.mark.unit]

  ### TestConnectedStreamsChaining (2 tests)
  - `test_chaining_transformations` [pytest.mark.unit]
  - `test_chaining_with_sink` [pytest.mark.unit]

  ### TestConnectedStreamsMultipleInputs (2 tests)
  - `test_two_input_streams` [pytest.mark.unit]
  - `test_multiple_input_streams` [pytest.mark.unit]

  ### TestConnectedStreamsIntegration (2 tests)
  - `test_complex_connection_workflow` [pytest.mark.integration]
  - `test_comap_integration` [pytest.mark.integration]

  ### TestConnectedStreamsEdgeCases (5 tests)
  - `test_empty_transformations_operations` [pytest.mark.unit]
  - `test_single_transformation_behavior` [pytest.mark.unit]
  - `test_none_function_handling` [pytest.mark.unit]
  - `test_multiple_operations_on_same_connected_streams` [pytest.mark.unit]
  - `test_transformation_order_preservation` [pytest.mark.unit]

## test_new_remote_env.py
- **Test Classes**: 0
- **Test Methods**: 0
- **Markers Used**: 
- **Lines of Code**: 128
- **Description**: 测试RemoteEnvironment序列化功能的简单脚本

## test_base_environment.py
- **Test Classes**: 12
- **Test Methods**: 36
- **Markers Used**: integration, unit
- **Lines of Code**: 693

  ### TestBaseEnvironmentInit (3 tests)
  - `test_init_with_defaults` [pytest.mark.unit]
  - `test_init_with_config` [pytest.mark.unit]
  - `test_init_with_empty_config` [pytest.mark.unit]

  ### TestBaseEnvironmentConsoleLogLevel (4 tests)
  - `test_set_console_log_level_valid` [pytest.mark.unit]
  - `test_set_console_log_level_case_insensitive` [pytest.mark.unit]
  - `test_set_console_log_level_invalid` [pytest.mark.unit]
  - `test_set_console_log_level_updates_existing_logger` [pytest.mark.unit]

  ### TestBaseEnvironmentServiceRegistration (2 tests)
  - `test_register_service_local` [pytest.mark.unit]
  - `test_register_service_remote` [pytest.mark.unit]

  ### TestBaseEnvironmentKafkaSource (2 tests)
  - `test_from_kafka_source_basic` [pytest.mark.unit]
  - `test_from_kafka_source_with_options` [pytest.mark.unit]

  ### TestBaseEnvironmentDataSources (4 tests)
  - `test_from_source_with_function_class` [pytest.mark.unit]
  - `test_from_source_with_lambda` [pytest.mark.unit]
  - `test_from_collection_with_function_class` [pytest.mark.unit]
  - `test_from_collection_with_lambda` [pytest.mark.unit]

  ### TestBaseEnvironmentFromBatch (7 tests)
  - `test_from_batch_with_function_class` [pytest.mark.unit]
  - `test_from_batch_with_list` [pytest.mark.unit]
  - `test_from_batch_with_tuple` [pytest.mark.unit]
  - `test_from_batch_with_range` [pytest.mark.unit]
  - `test_from_batch_with_set` [pytest.mark.unit]
  - ... and 2 more tests

  ### TestBaseEnvironmentFromFuture (1 tests)
  - `test_from_future` [pytest.mark.unit]

  ### TestBaseEnvironmentProperties (3 tests)
  - `test_logger_property_lazy_creation` [pytest.mark.unit]
  - `test_client_property_lazy_creation` [pytest.mark.unit]
  - `test_client_property_with_config` [pytest.mark.unit]

  ### TestBaseEnvironmentLoggingSetup (1 tests)
  - `test_setup_logging_system` [pytest.mark.unit]

  ### TestBaseEnvironmentAuxiliaryMethods (4 tests)
  - `test_append_method` [pytest.mark.unit]
  - `test_from_batch_collection_internal` [pytest.mark.unit]
  - `test_from_batch_iterable_internal` [pytest.mark.unit]
  - `test_from_batch_iterable_without_len` [pytest.mark.unit]

  ### TestBaseEnvironmentEdgeCases (3 tests)
  - `test_empty_config_handling` [pytest.mark.unit]
  - `test_state_exclude_attribute` [pytest.mark.unit]
  - `test_abstract_methods_exist` [pytest.mark.unit]

  ### TestBaseEnvironmentIntegration (2 tests)
  - `test_full_pipeline_creation` [pytest.mark.integration]
  - `test_service_registration_workflow` [pytest.mark.integration]

## test_datastream.py
- **Test Classes**: 10
- **Test Methods**: 31
- **Markers Used**: integration, unit
- **Lines of Code**: 543
- **Description**: Tests for sage

  ### TestDataStreamInit (3 tests)
  - `test_init_basic` [pytest.mark.unit]
  - `test_init_logger_creation` [pytest.mark.unit]
  - `test_init_type_param_resolution` [pytest.mark.unit]

  ### TestDataStreamTransformations (11 tests)
  - `test_map_with_function_class` [pytest.mark.unit]
  - `test_map_with_lambda` [pytest.mark.unit]
  - `test_filter_with_function_class` [pytest.mark.unit]
  - `test_filter_with_lambda` [pytest.mark.unit]
  - `test_flatmap_with_function_class` [pytest.mark.unit]
  - ... and 6 more tests

  ### TestDataStreamConnect (2 tests)
  - `test_connect_with_datastream` [pytest.mark.unit]
  - `test_connect_with_connected_streams` [pytest.mark.unit]

  ### TestDataStreamFillFuture (3 tests)
  - `test_fill_future_successful` [pytest.mark.unit]
  - `test_fill_future_not_future_stream` [pytest.mark.unit]
  - `test_fill_future_already_filled` [pytest.mark.unit]

  ### TestDataStreamPrint (2 tests)
  - `test_print_with_defaults` [pytest.mark.unit]
  - `test_print_with_custom_params` [pytest.mark.unit]

  ### TestDataStreamApply (1 tests)
  - `test_apply_method` [pytest.mark.unit]

  ### TestDataStreamTypeResolution (2 tests)
  - `test_resolve_type_param_fallback` [pytest.mark.unit]
  - `test_resolve_type_param_with_orig_class` [pytest.mark.unit]

  ### TestDataStreamChaining (2 tests)
  - `test_chaining_transformations` [pytest.mark.unit]
  - `test_chaining_with_sink` [pytest.mark.unit]

  ### TestDataStreamIntegration (2 tests)
  - `test_complex_pipeline` [pytest.mark.integration]
  - `test_future_stream_workflow` [pytest.mark.integration]

  ### TestDataStreamEdgeCases (3 tests)
  - `test_empty_pipeline_operations` [pytest.mark.unit]
  - `test_none_function_handling` [pytest.mark.unit]
  - `test_multiple_sink_operations` [pytest.mark.unit]

## test_remote_environment.py
- **Test Classes**: 8
- **Test Methods**: 26
- **Markers Used**: integration, unit
- **Lines of Code**: 477
- **Description**: Tests for sage

  ### TestRemoteEnvironmentInit (4 tests)
  - `test_init_with_defaults` [pytest.mark.unit]
  - `test_init_with_custom_params` [pytest.mark.unit]
  - `test_init_with_none_config` [pytest.mark.unit]
  - `test_state_exclude_attributes` [pytest.mark.unit]

  ### TestRemoteEnvironmentClient (2 tests)
  - `test_client_property_lazy_creation` [pytest.mark.unit]
  - `test_client_property_with_custom_host_port` [pytest.mark.unit]

  ### TestRemoteEnvironmentSubmit (5 tests)
  - `test_submit_successful` [pytest.mark.unit]
  - `test_submit_failure_response` [pytest.mark.unit]
  - `test_submit_success_without_uuid` [pytest.mark.unit]
  - `test_submit_serialization_error` [pytest.mark.unit]
  - `test_submit_client_error` [pytest.mark.unit]

  ### TestRemoteEnvironmentGetQd (3 tests)
  - `test_get_qd_default_params` [pytest.mark.unit]
  - `test_get_qd_custom_params` [pytest.mark.unit]
  - `test_get_qd_different_names` [pytest.mark.unit]

  ### TestRemoteEnvironmentInheritance (3 tests)
  - `test_inherits_from_base_environment` [pytest.mark.unit]
  - `test_platform_is_remote` [pytest.mark.unit]
  - `test_inherited_methods_available` [pytest.mark.unit]

  ### TestRemoteEnvironmentLogging (3 tests)
  - `test_init_logging` [pytest.mark.unit]
  - `test_client_creation_logging` [pytest.mark.unit]
  - `test_submit_logging` [pytest.mark.unit]

  ### TestRemoteEnvironmentIntegration (2 tests)
  - `test_full_workflow` [pytest.mark.integration]
  - `test_multiple_queue_descriptors` [pytest.mark.integration]

  ### TestRemoteEnvironmentEdgeCases (4 tests)
  - `test_config_merging` [pytest.mark.unit]
  - `test_multiple_submit_calls` [pytest.mark.unit]
  - `test_attributes_exist_after_init` [pytest.mark.unit]
  - `test_client_property_thread_safety` [pytest.mark.unit]

## test_local_environment.py
- **Test Classes**: 9
- **Test Methods**: 27
- **Markers Used**: integration, unit
- **Lines of Code**: 450
- **Description**: Tests for sage

  ### TestLocalEnvironmentInit (3 tests)
  - `test_init_with_defaults` [pytest.mark.unit]
  - `test_init_with_custom_name_and_config` [pytest.mark.unit]
  - `test_init_with_none_config` [pytest.mark.unit]

  ### TestLocalEnvironmentJobManager (2 tests)
  - `test_jobmanager_property_lazy_creation` [pytest.mark.unit]
  - `test_jobmanager_property_singleton` [pytest.mark.unit]

  ### TestLocalEnvironmentSubmit (2 tests)
  - `test_submit_job` [pytest.mark.unit]
  - `test_submit_returns_none` [pytest.mark.unit]

  ### TestLocalEnvironmentStop (4 tests)
  - `test_stop_without_env_uuid` [pytest.mark.unit]
  - `test_stop_successful` [pytest.mark.unit]
  - `test_stop_failure_response` [pytest.mark.unit]
  - `test_stop_exception_handling` [pytest.mark.unit]

  ### TestLocalEnvironmentClose (4 tests)
  - `test_close_without_env_uuid` [pytest.mark.unit]
  - `test_close_successful` [pytest.mark.unit]
  - `test_close_failure_response` [pytest.mark.unit]
  - `test_close_exception_handling` [pytest.mark.unit]

  ### TestLocalEnvironmentGetQd (3 tests)
  - `test_get_qd_default_params` [pytest.mark.unit]
  - `test_get_qd_custom_params` [pytest.mark.unit]
  - `test_get_qd_different_names` [pytest.mark.unit]

  ### TestLocalEnvironmentInheritance (4 tests)
  - `test_inherits_from_base_environment` [pytest.mark.unit]
  - `test_platform_is_local` [pytest.mark.unit]
  - `test_inherited_methods_available` [pytest.mark.unit]
  - `test_no_engine_client_in_local` [pytest.mark.unit]

  ### TestLocalEnvironmentIntegration (2 tests)
  - `test_full_workflow` [pytest.mark.integration]
  - `test_multiple_queue_descriptors` [pytest.mark.integration]

  ### TestLocalEnvironmentEdgeCases (3 tests)
  - `test_stop_close_without_logger` [pytest.mark.unit]
  - `test_multiple_close_calls` [pytest.mark.unit]
  - `test_attributes_exist_after_init` [pytest.mark.unit]

## test_remote_env_serialization.py
- **Test Classes**: 0
- **Test Methods**: 0
- **Markers Used**: 
- **Lines of Code**: 211
- **Description**: 测试RemoteEnvironment的序列化提交流程

## test_from_batch_polymorphism.py
- **Test Classes**: 0
- **Test Methods**: 0
- **Markers Used**: 
- **Lines of Code**: 142
- **Description**: 测试改进后的 from_batch 接口的多态性

## test_remote_environment_server.py
- **Test Classes**: 0
- **Test Methods**: 0
- **Markers Used**: 
- **Lines of Code**: 1120
- **Description**: 远程环境服务端测试脚本
用于接收序列化的环境并验证其完整性

这个文件既可以作为独立的测试服务器运行，也可以通过pytest运行标准测试。

独立运行Usage:
    # 运行完整的RemoteEnvironment序列化测试
    python test_remote_environment_server
