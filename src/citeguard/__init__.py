from .cache import FileCache
from .checker import check_doi, check_dois
from .crossref import CrossrefError, DoiNotFoundError, build_fetcher, polite_fetcher
from .models import Citation, RetractionStatus, Signal, SignalType, Verdict
from .parsers import extract_dois, parse_bibtex, parse_ris

__version__ = "0.1.0"

__all__ = [
    "check_doi",
    "check_dois",
    "FileCache",
    "build_fetcher",
    "polite_fetcher",
    "CrossrefError",
    "DoiNotFoundError",
    "Citation",
    "RetractionStatus",
    "Signal",
    "SignalType",
    "Verdict",
    "extract_dois",
    "parse_bibtex",
    "parse_ris",
    "__version__",
]
