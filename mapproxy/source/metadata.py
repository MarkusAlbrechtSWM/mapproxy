# This file is part of the MapProxy project.
# Copyright (C) 2025 Omniscale <http://omniscale.de>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Automatic metadata extraction from WMS sources.
"""

import logging
import time
from io import BytesIO
from urllib.parse import urlparse, parse_qs

from mapproxy.util.ext.wmsparse import parse_capabilities
from mapproxy.client.http import HTTPClient

log = logging.getLogger(__name__)


class WMSMetadataManager:
    """Manager for fetching and processing WMS metadata from GetCapabilities."""
    
    def __init__(self):
        self._cache = {}  # Simple memory cache for capabilities documents
        self._cache_ttl = 300  # 5 minutes cache TTL
    
    def get_wms_metadata(self, wms_url, auth_config=None, target_layer=None):
        """
        Fetch WMS metadata from GetCapabilities document.
        
        Args:
            wms_url: WMS service URL
            auth_config: Authentication configuration (username, password, headers)
            target_layer: Specific layer name to extract metadata for
            
        Returns:
            dict: Metadata dictionary with service and/or layer metadata
        """
        cache_key = f"{wms_url}|{target_layer}"
        
        # Check cache first
        if cache_key in self._cache:
            cached_time, metadata = self._cache[cache_key]
            if time.time() - cached_time < self._cache_ttl:
                log.debug(f"Using cached metadata for {wms_url}")
                return metadata
        
        try:
            # Fetch GetCapabilities document
            cap_doc = self._fetch_capabilities(wms_url, auth_config)
            
            # Parse capabilities
            capabilities = parse_capabilities(BytesIO(cap_doc))
            
            # Extract metadata
            metadata = self._extract_metadata(capabilities, target_layer)
            
            # Cache the result
            self._cache[cache_key] = (time.time(), metadata)
            
            return metadata
            
        except Exception as e:
            log.warning(f"Failed to fetch metadata from {wms_url}: {e}")
            return {}
    
    def _fetch_capabilities(self, wms_url, auth_config=None):
        """Fetch GetCapabilities document from WMS URL."""
        
        # Build GetCapabilities URL
        parsed_url = urlparse(wms_url)
        query_params = parse_qs(parsed_url.query)
        
        # Add GetCapabilities parameters - no default version
        query_params.update({
            'SERVICE': ['WMS'],
            'REQUEST': ['GetCapabilities']
        })
        
        # Reconstruct URL with GetCapabilities parameters
        from urllib.parse import urlencode, urlunparse
        new_query = urlencode(query_params, doseq=True)
        cap_url = urlunparse((
            parsed_url.scheme, parsed_url.netloc, parsed_url.path,
            parsed_url.params, new_query, parsed_url.fragment
        ))
        
        # Setup HTTP client with authentication
        headers = {}
        username = None
        password = None
        
        if auth_config:
            if 'username' in auth_config and 'password' in auth_config:
                username = auth_config['username']
                password = auth_config['password']
            
            if 'headers' in auth_config:
                headers.update(auth_config['headers'])
        
        # Create HTTP client with auth configuration
        http_client = HTTPClient(
            url=cap_url,
            username=username,
            password=password,
            headers=headers
        )
        
        # Fetch the document
        log.debug(f"Fetching GetCapabilities from {cap_url}")
        response = http_client.open(cap_url)
        
        if response.code != 200:
            raise Exception(f"HTTP {response.code}: {response.read()}")
        
        return response.read()
    
    def _extract_metadata(self, capabilities, target_layer=None):
        """Extract metadata from parsed capabilities."""
        metadata = {}
        
        # Extract service-level metadata
        service_md = capabilities.metadata()
        if service_md:
            metadata['service'] = {
                'title': service_md.get('title'),
                'abstract': service_md.get('abstract'),
                'contact': service_md.get('contact'),
                'fees': service_md.get('fees'),
                'access_constraints': service_md.get('access_constraints'),
            }
        
        # Extract layer-specific metadata if target_layer specified
        if target_layer:
            layer_md = self._find_layer_metadata(capabilities, target_layer)
            if layer_md:
                metadata['layer'] = layer_md
        
        return metadata
    
    def _find_layer_metadata(self, capabilities, layer_name):
        """Find and extract metadata for a specific layer."""
        layers = capabilities.layers_list()
        
        # Try exact match first
        for layer in layers:
            if layer.get('name') == layer_name:
                return self._process_layer_metadata(layer)
        
        # Try case-insensitive match
        layer_name_lower = layer_name.lower()
        for layer in layers:
            if layer.get('name', '').lower() == layer_name_lower:
                return self._process_layer_metadata(layer)
        
        # Try partial match (contains)
        for layer in layers:
            if layer_name_lower in layer.get('name', '').lower():
                return self._process_layer_metadata(layer)
        
        log.warning(f"Layer '{layer_name}' not found in WMS capabilities")
        return {}
    
    def _process_layer_metadata(self, layer):
        """Process and format layer metadata."""
        metadata = {}
        
        # Title
        if layer.get('title'):
            metadata['title'] = layer['title']
        
        # Abstract (with title prepending)
        abstract = layer.get('abstract')
        title = layer.get('title')
        
        if abstract and title:
            # Prepend title to abstract
            metadata['abstract'] = f"{title}: {abstract}"
        elif abstract:
            metadata['abstract'] = abstract
        elif title:
            metadata['abstract'] = title
                
        # Attribution
        legend = layer.get('legend')
        if legend:
            metadata['attribution'] = {
                'title': f"Layer: {layer.get('name', '')}",
                'url': legend.get('url', '')
            }
        
        # Contact (would need to be extracted from service level)
        # This could be enhanced to extract layer-specific contact if available
        
        return metadata


def merge_auto_metadata(manual_metadata, auto_metadata):
    """
    Merge auto-fetched metadata with manual configuration.
    Manual configuration takes priority over auto metadata.
    """
    if not auto_metadata:
        return manual_metadata or {}
    
    merged = auto_metadata.copy()
    
    if manual_metadata:
        # Manual metadata overrides auto metadata
        for key, value in manual_metadata.items():
            if value is not None:
                merged[key] = value
    
    return merged