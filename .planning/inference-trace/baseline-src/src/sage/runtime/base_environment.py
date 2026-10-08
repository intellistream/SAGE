from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from sage.foundation import CustomLogger, wrap_lambda
from sage.stream.transformations import (
    BaseTransformation,
    BatchTransformation,
    FutureTransformation,
    SourceTransformation,
)

from .batch_functions import IterableBatchIteratorFunction, SimpleBatchIteratorFunction
from .jobmanager_client import JobManagerClient
from .scheduler import resolve_scheduler
from .service_factory import ServiceFactory

if TYPE_CHECKING:
    from sage.foundation.core import BaseFunction
    from sage.stream import DataStream


class BaseEnvironment(ABC):
    __state_exclude__ = ["_engine_client", "client", "jobmanager"]

    def _get_datastream_class(self):
        if not hasattr(self, "_datastream_class"):
            from sage.stream import DataStream

            self._datastream_class = DataStream
        return self._datastream_class

    def _get_transformation_classes(self):
        if not hasattr(self, "_transformation_classes"):
            self._transformation_classes = {
                "BaseTransformation": BaseTransformation,
                "SourceTransformation": SourceTransformation,
                "BatchTransformation": BatchTransformation,
                "FutureTransformation": FutureTransformation,
            }
        return self._transformation_classes

    def __init__(
        self,
        name: str,
        config: dict | None,
        *,
        platform: str = "local",
        scheduler=None,
        enable_monitoring: bool = False,
    ):
        self.name = name
        self.uuid: str | None = None

        self.config: dict = dict(config or {})
        self.platform: str = platform

        self.jobmanager_host: str | None = None
        self.jobmanager_port: int | None = None
        self.session_id: str | None = None
        self.session_timestamp: Any | None = None
        self.pipeline: list[BaseTransformation] = []
        self._filled_futures: dict = {}
        self.service_factories: dict = {}

        self.enable_monitoring: bool = enable_monitoring

        self._scheduler = None
        self._init_scheduler(scheduler)

        self.env_base_dir: str | None = None
        self._jobmanager: Any | None = None
        self._engine_client: JobManagerClient | None = None
        self.env_uuid: str | None = None
        self.console_log_level: str = "INFO"

    def _init_scheduler(self, scheduler):
        self._scheduler = resolve_scheduler(scheduler=scheduler, platform=self.platform)

    @property
    def scheduler(self):
        return self._scheduler

    def set_console_log_level(self, level: str):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
        if level.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {level}. Must be one of {valid_levels}")

        self.console_log_level = level.upper()

        if hasattr(self, "_logger") and self._logger is not None:
            self._logger.update_output_level("console", self.console_log_level)

    def register_service(self, service_name: str, service_class: type, *args, **kwargs):
        service_factory = ServiceFactory(
            service_name=service_name,
            service_class=service_class,
            service_args=args,
            service_kwargs=kwargs,
        )

        self.service_factories[service_name] = service_factory
        platform_str = "remote" if self.platform == "remote" else "local"
        self.logger.info(
            f"Registered {platform_str} service: {service_name} ({service_class.__name__})"
        )
        return service_factory

    def register_service_factory(self, service_name: str, service_factory: ServiceFactory):
        self.service_factories[service_name] = service_factory
        platform_str = "remote" if self.platform == "remote" else "local"
        self.logger.info(f"Registered {platform_str} service factory: {service_name}")
        return service_factory

    def from_kafka_source(
        self,
        source_class: type,
        bootstrap_servers: str,
        topic: str,
        group_id: str,
        auto_offset_reset: str = "latest",
        value_deserializer: str = "json",
        buffer_size: int = 10000,
        max_poll_records: int = 500,
        **kafka_config,
    ) -> DataStream:
        SourceTransformation = self._get_transformation_classes()["SourceTransformation"]
        transformation = SourceTransformation(
            self,
            source_class,
            bootstrap_servers=bootstrap_servers,
            topic=topic,
            group_id=group_id,
            auto_offset_reset=auto_offset_reset,
            value_deserializer=value_deserializer,
            buffer_size=buffer_size,
            max_poll_records=max_poll_records,
            **kafka_config,
        )

        self.pipeline.append(transformation)
        self.logger.info(f"Kafka source created for topic: {topic}, group: {group_id}")
        return self._get_datastream_class()(self, transformation)

    def from_source(self, function: type[BaseFunction] | Callable, *args, **kwargs) -> DataStream:
        if callable(function) and not isinstance(function, type):
            function = wrap_lambda(function, "flatmap")

        SourceTransformation = self._get_transformation_classes()["SourceTransformation"]
        transformation = SourceTransformation(self, function, *args, **kwargs)
        self.pipeline.append(transformation)
        return self._get_datastream_class()(self, transformation)

    def from_collection(
        self, function: type[BaseFunction] | Callable, *args, **kwargs
    ) -> DataStream:
        if callable(function) and not isinstance(function, type):
            function = wrap_lambda(function, "flatmap")

        BatchTransformation = self._get_transformation_classes()["BatchTransformation"]
        transformation = BatchTransformation(self, function, *args, **kwargs)
        self.pipeline.append(transformation)
        return self._get_datastream_class()(self, transformation)

    def from_batch(self, source: type[BaseFunction] | Any, *args, **kwargs) -> DataStream:
        if isinstance(source, type) and hasattr(source, "__bases__"):
            from sage.foundation import BaseFunction

            if issubclass(source, BaseFunction):
                return self._from_batch_function_class(source, *args, **kwargs)

        if isinstance(source, (list, tuple)):
            return self._from_batch_collection(source, **kwargs)
        if hasattr(source, "__iter__") and not isinstance(source, (str, bytes)):
            return self._from_batch_iterable(source, **kwargs)
        if isinstance(source, (str, bytes)):
            return self._from_batch_iterable(source, **kwargs)

        try:
            iter(source)
            return self._from_batch_iterable(source, **kwargs)
        except TypeError:
            raise TypeError(
                f"Unsupported source type: {type(source)}. Expected BaseFunction subclass, list, tuple, or any iterable object."
            ) from None

    def from_future(self, name: str) -> DataStream:
        FutureTransformation = self._get_transformation_classes()["FutureTransformation"]
        transformation = FutureTransformation(self, name)
        self.pipeline.append(transformation)
        return self._get_datastream_class()(self, transformation)

    @abstractmethod
    def submit(self):
        pass

    @property
    def logger(self):
        if not hasattr(self, "_logger"):
            self._logger = CustomLogger()
        return self._logger

    @property
    def client(self) -> JobManagerClient:
        if self._engine_client is None:
            daemon_host = self.config.get("engine_host", "127.0.0.1")
            daemon_port = self.config.get("engine_port", 19000)
            self._engine_client = JobManagerClient(host=daemon_host, port=daemon_port)
        return self._engine_client

    def _append(self, transformation: BaseTransformation):
        self.pipeline.append(transformation)
        return self._get_datastream_class()(self, transformation)

    def _from_batch_function_class(
        self, batch_function_class: type[BaseFunction], *args, **kwargs
    ) -> DataStream:
        transform_kwargs = {}
        function_kwargs = {}
        transform_config_keys = {"delay", "progress_log_interval"}

        for key, value in kwargs.items():
            if key in transform_config_keys:
                transform_kwargs[key] = value
            else:
                function_kwargs[key] = value

        BatchTransformation = self._get_transformation_classes()["BatchTransformation"]
        transformation = BatchTransformation(
            self, batch_function_class, *args, **function_kwargs, **transform_kwargs
        )

        self.pipeline.append(transformation)
        self.logger.info(f"Custom batch source created with {batch_function_class.__name__}")
        return self._get_datastream_class()(self, transformation)

    def _from_batch_collection(self, data: list | tuple, **kwargs) -> DataStream:
        BatchTransformation = self._get_transformation_classes()["BatchTransformation"]
        transformation = BatchTransformation(self, SimpleBatchIteratorFunction, data=data, **kwargs)

        self.pipeline.append(transformation)
        self.logger.info(f"Batch collection source created with {len(data)} items")
        return self._get_datastream_class()(self, transformation)

    def _from_batch_iterable(self, iterable: Any, **kwargs) -> DataStream:
        total_count = kwargs.pop("total_count", None)
        if total_count is None:
            try:
                total_count = len(iterable)
            except TypeError:
                total_count = None

        BatchTransformation = self._get_transformation_classes()["BatchTransformation"]
        transformation = BatchTransformation(
            self,
            IterableBatchIteratorFunction,
            iterable=iterable,
            total_count=total_count,
            **kwargs,
        )

        self.pipeline.append(transformation)
        type_name = type(iterable).__name__
        count_info = f" with {total_count} items" if total_count is not None else ""
        self.logger.info(f"Batch iterable source created from {type_name}{count_info}")
        return self._get_datastream_class()(self, transformation)
