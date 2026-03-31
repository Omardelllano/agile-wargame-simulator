class WargameError(Exception): pass
class GroundingError(WargameError): pass
class ProviderError(WargameError): pass
class ScenarioNotFoundError(WargameError): pass
class LowConfidenceError(WargameError): pass
class SchemaValidationError(WargameError): pass
