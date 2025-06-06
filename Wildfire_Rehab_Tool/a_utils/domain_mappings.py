# Step 6
"""
This module stores reusable domain mappings for both points and lines,
as well as a helper function to normalize labels consistently.
"""

# Wildfire_Rehab_Tool/a_utils/domain_mappings.py

import re

def normalize_label(label):
    """Normalize label by removing punctuation, whitespace, and lowering case."""
    return re.sub(r'[^a-zA-Z0-9]', '', label).lower()

# Domain mapping for points
POINT_DOMAIN_MAPPING = {
    'ditchcleanrepairdcr': '14',
    'dryseedds': '19',
    'pullbackpb': '30',
    'recontourrc': '31',
    'steepslopesss': '36',
    'notreatmentpointnt': '41',
    'noworkzonenwz': '56',
    'infrastructurerepairir': '54',
    'infrastructurenotreatmentint': '53',
    'hazardh': '27',
    'otherrehabtreatmenttypeort': '46'
}

# Domain mapping for lines
LINE_DOMAIN_MAPPING = {
    'ditchcleanrepairdcr': '1',
    'dryseedds': '2',
    'graderoadgr': '5',
    'pullbackpb': '6',
    'recontourrc': '7',
    'steepslopesss': '10',
    'notreatmentnaline': '11',
    'firehazardtreatmentfht': '13',
    'otherrehabtreatmenttypeort': '16',
    'infrastructurerepairir': '20',
    'infrastructurenotreatmentint': '21',
    'noworkzonenwz': '22',
    'unknown': '0',
    'activeburnout': '1',
    'completedmachine': '9',
    'completedhandline': '10',
    'road': '31',
    'trail': '34',
    'containmentcontrolline': '37',
    '5m': '0',
    '10m': '1',
    '15m': '2',
    '20mandwider': '3',
    '0to15': '0',
    '16to25': '1',
    '26to35': '2',
    'above35': '3'
}
