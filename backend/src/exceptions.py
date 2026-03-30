"""
Custom exception classes for the VPP application.
"""


class VPPException(Exception):
    """Base exception class for VPP application."""

    pass


class DatabaseException(VPPException):
    """Raised when database operations fail."""

    pass


class ConnectionException(DatabaseException):
    """Raised when database connection fails."""

    pass


class QueryException(DatabaseException):
    """Raised when a database query fails."""

    pass


class ModelException(VPPException):
    """Base exception for model-related errors."""

    pass


class ModelNotFoundError(ModelException):
    """Raised when a model is not found in MLflow registry."""

    pass


class ModelLoadError(ModelException):
    """Raised when model loading fails."""

    pass


class ModelTrainingError(ModelException):
    """Raised when model training fails."""

    pass


class ModelPredictionError(ModelException):
    """Raised when model prediction fails."""

    pass


class DataException(VPPException):
    """Base exception for data-related errors."""

    pass


class DataNotFoundError(DataException):
    """Raised when required data is not found."""

    pass


class DataValidationError(DataException):
    """Raised when data validation fails."""

    pass


class InvalidTableNameError(DataException):
    """Raised when an invalid table name is provided."""

    pass


class KafkaException(VPPException):
    """Base exception for Kafka-related errors."""

    pass


class KafkaProducerError(KafkaException):
    """Raised when Kafka producer fails."""

    pass


class KafkaConsumerError(KafkaException):
    """Raised when Kafka consumer fails."""

    pass


class OptimizationException(VPPException):
    """Base exception for optimization-related errors."""

    pass


class OptimizationInfeasibleError(OptimizationException):
    """Raised when optimization problem is infeasible."""

    pass


class BatteryException(VPPException):
    """Base exception for battery-related errors."""

    pass


class BatteryNotFoundError(BatteryException):
    """Raised when battery is not found."""

    pass


class BatteryOperationError(BatteryException):
    """Raised when battery operation (charge/discharge) fails."""

    pass


class ConfigurationException(VPPException):
    """Raised when configuration is invalid or missing."""

    pass
