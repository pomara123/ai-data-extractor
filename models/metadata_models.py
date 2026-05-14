from pydantic import BaseModel
from typing import Optional, List


class Metadata(BaseModel):
    # Core dataset descriptors
    experiment_id: Optional[str] = None
    data_source: Optional[str] = None
    data_retention: Optional[str] = None
    function: Optional[str] = None
    file_type: Optional[str] = None
    modality: Optional[str] = None

    # Experimental biology context
    species: Optional[str] = None
    cell_line: Optional[str] = None
    treatment: Optional[str] = None

    # Instrumentation
    microscopy_type: Optional[str] = None
    instrument_name: Optional[str] = None

    # Biological markers (can be multi-valued)
    marker: Optional[List[str]] = None