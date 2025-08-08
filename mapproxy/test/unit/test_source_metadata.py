"""
Unit tests for WMS metadata manager functionality.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from mapproxy.source.metadata import WMSMetadataManager
from mapproxy.client.http import HTTPClientError


class TestWMSMetadataManager:
    
    def setup_method(self):
        """Setup test fixtures."""
        self.manager = WMSMetadataManager()
    
    def test_init(self):
        """Test WMSMetadataManager initialization."""
        assert self.manager.capabilities_cache == {}
    
    @patch('mapproxy.source.metadata.HTTPClient')
    def test_fetch_capabilities_success(self, mock_http_client):
        """Test successful GetCapabilities request."""
        # Setup mock response
        mock_client_instance = Mock()
        mock_http_client.return_value = mock_client_instance
        
        mock_response = Mock()
        mock_response.read.return_value = b"""<?xml version="1.0" encoding="UTF-8"?>
        <WMS_Capabilities version="1.3.0">
            <Service>
                <Title>Test WMS Service</Title>
                <Abstract>Test service description</Abstract>
            </Service>
            <Capability>
                <Layer>
                    <Name>test_layer</Name>
                    <Title>Test Layer</Title>
                    <Abstract>Test layer description</Abstract>
                </Layer>
            </Capability>
        </WMS_Capabilities>"""
        
        mock_client_instance.open.return_value = mock_response
        
        # Test method
        result = self.manager._fetch_capabilities("http://example.com/wms", {})
        
        # Verify result
        assert result is not None
        assert "Test WMS Service" in str(result)
        
        # Verify HTTP client was called correctly
        mock_http_client.assert_called_once()
        mock_client_instance.open.assert_called_once()
    
    @patch('mapproxy.source.metadata.HTTPClient')
    def test_fetch_capabilities_with_auth(self, mock_http_client):
        """Test GetCapabilities request with authentication."""
        mock_client_instance = Mock()
        mock_http_client.return_value = mock_client_instance
        
        mock_response = Mock()
        mock_response.read.return_value = b'<WMS_Capabilities version="1.3.0"></WMS_Capabilities>'
        mock_client_instance.open.return_value = mock_response
        
        auth_config = {
            'username': 'testuser',
            'password': 'testpass',
            'headers': {'X-API-Key': 'secret'}
        }
        
        self.manager._fetch_capabilities("http://example.com/wms", auth_config)
        
        # Verify HTTP client was configured with auth
        mock_http_client.assert_called_once()
        args, kwargs = mock_http_client.call_args
        assert 'username' in kwargs
        assert kwargs['username'] == 'testuser'
        assert 'password' in kwargs
        assert kwargs['password'] == 'testpass'
    
    @patch('mapproxy.source.metadata.HTTPClient')
    def test_fetch_capabilities_http_error(self, mock_http_client):
        """Test GetCapabilities request with HTTP error."""
        mock_client_instance = Mock()
        mock_http_client.return_value = mock_client_instance
        mock_client_instance.open.side_effect = HTTPClientError("Connection failed")
        
        result = self.manager._fetch_capabilities("http://example.com/wms", {})
        assert result is None
    
    @patch('mapproxy.source.metadata.HTTPClient')
    def test_fetch_capabilities_caching(self, mock_http_client):
        """Test that GetCapabilities responses are cached."""
        mock_client_instance = Mock()
        mock_http_client.return_value = mock_client_instance
        
        mock_response = Mock()
        mock_response.read.return_value = b'<WMS_Capabilities version="1.3.0"></WMS_Capabilities>'
        mock_client_instance.open.return_value = mock_response
        
        url = "http://example.com/wms"
        
        # First call
        result1 = self.manager._fetch_capabilities(url, {})
        
        # Second call should use cache
        result2 = self.manager._fetch_capabilities(url, {})
        
        # Verify HTTP client was only called once
        assert mock_http_client.call_count == 1
        assert result1 is result2  # Same object from cache
    
    @patch.object(WMSMetadataManager, '_fetch_capabilities')
    def test_get_layer_metadata_capabilities_error(self, mock_fetch):
        """Test layer metadata retrieval when GetCapabilities fails."""
        mock_fetch.return_value = None
        
        metadata = self.manager.get_layer_metadata("http://example.com/wms", "test_layer", {})
        
        assert metadata == {}
    
    @patch.object(WMSMetadataManager, '_fetch_capabilities')
    def test_get_service_metadata_success(self, mock_fetch):
        """Test successful service metadata retrieval."""
        capabilities_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <WMS_Capabilities version="1.3.0">
            <Service>
                <Title>Test Service</Title>
                <Abstract>Test service description</Abstract>
            </Service>
        </WMS_Capabilities>"""
        
        from xml.etree import ElementTree as ET
        mock_fetch.return_value = ET.fromstring(capabilities_xml)
        
        metadata = self.manager.get_service_metadata("http://example.com/wms", {})
        
        assert metadata['title'] == 'Test Service'
        assert metadata['abstract'] == 'Test service description'
    
    @patch.object(WMSMetadataManager, '_fetch_capabilities')
    def test_get_service_metadata_capabilities_error(self, mock_fetch):
        """Test service metadata retrieval when GetCapabilities fails."""
        mock_fetch.return_value = None
        
        metadata = self.manager.get_service_metadata("http://example.com/wms", {})
        
        assert metadata == {}


class TestWMSMetadataManagerIntegration:
    """Integration tests that test the metadata manager with real XML responses."""
    
    def setup_method(self):
        self.manager = WMSMetadataManager()
    
    def test_complex_capabilities_document(self):
        """Test with a complex capabilities document similar to real WMS services."""
        capabilities_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <WMS_Capabilities version="1.3.0" xmlns="http://www.opengis.net/wms">
            <Service>
                <Name>WMS</Name>
                <Title>Test WMS Service</Title>
                <Abstract>Comprehensive test service for metadata extraction</Abstract>
                <KeywordList>
                    <Keyword>mapping</Keyword>
                    <Keyword>GIS</Keyword>
                </KeywordList>
                <OnlineResource xmlns:xlink="http://www.w3.org/1999/xlink" xlink:href="http://example.com"/>
                <ContactInformation>
                    <ContactPersonPrimary>
                        <ContactPerson>Jane Smith</ContactPerson>
                        <ContactOrganization>Mapping Solutions Inc</ContactOrganization>
                    </ContactPersonPrimary>
                    <ContactPosition>GIS Manager</ContactPosition>
                    <ContactAddress>
                        <AddressType>postal</AddressType>
                        <Address>123 Map Street</Address>
                        <City>Cartography</City>
                        <StateOrProvince>GIS</StateOrProvince>
                        <PostCode>12345</PostCode>
                        <Country>Mapland</Country>
                    </ContactAddress>
                    <ContactVoiceTelephone>+1-555-123-4567</ContactVoiceTelephone>
                    <ContactElectronicMailAddress>jane@mappingsolutions.com</ContactElectronicMailAddress>
                </ContactInformation>
                <Fees>Commercial use requires license</Fees>
                <AccessConstraints>Licensed data</AccessConstraints>
            </Service>
            <Capability>
                <Request>
                    <GetCapabilities>
                        <Format>text/xml</Format>
                    </GetCapabilities>
                    <GetMap>
                        <Format>image/png</Format>
                        <Format>image/jpeg</Format>
                    </GetMap>
                </Request>
                <Layer>
                    <Title>Root Layer</Title>
                    <CRS>EPSG:4326</CRS>
                    <CRS>EPSG:3857</CRS>
                    <Layer queryable="1">
                        <Name>administrative_boundaries</Name>
                        <Title>Administrative Boundaries</Title>
                        <Abstract>Political and administrative boundary data</Abstract>
                        <KeywordList>
                            <Keyword>boundaries</Keyword>
                            <Keyword>administrative</Keyword>
                        </KeywordList>
                        <Attribution>
                            <Title>National Mapping Agency</Title>
                            <OnlineResource xmlns:xlink="http://www.w3.org/1999/xlink" xlink:href="http://mapping.gov"/>
                        </Attribution>
                        <Layer>
                            <Name>countries</Name>
                            <Title>Country Boundaries</Title>
                            <Abstract>International country boundaries</Abstract>
                        </Layer>
                        <Layer>
                            <Name>states</Name>
                            <Title>State Boundaries</Title>
                            <Abstract>State and province boundaries</Abstract>
                        </Layer>
                    </Layer>
                    <Layer queryable="1">
                        <Name>transportation</Name>
                        <Title>Transportation Network</Title>
                        <Abstract>Roads, railways, and transportation infrastructure</Abstract>
                        <Attribution>
                            <Title>Department of Transportation</Title>
                        </Attribution>
                    </Layer>
                </Layer>
            </Capability>
        </WMS_Capabilities>"""
        
        from xml.etree import ElementTree as ET
        capabilities = ET.fromstring(capabilities_xml)
        
        # Test service metadata extraction
        service_metadata = self.manager._extract_service_metadata(capabilities)
        
        assert service_metadata['title'] == 'Test WMS Service'
        assert service_metadata['abstract'] == 'Comprehensive test service for metadata extraction'
        assert service_metadata['fees'] == 'Commercial use requires license'
        assert service_metadata['access_constraints'] == 'Licensed data'
        
        contact = service_metadata['contact']
        assert contact['person'] == 'Jane Smith'
        assert contact['organization'] == 'Mapping Solutions Inc'
        assert contact['position'] == 'GIS Manager'
        assert contact['email'] == 'jane@mappingsolutions.com'
        assert contact['phone'] == '+1-555-123-4567'
        assert contact['address'] == '123 Map Street'
        assert contact['city'] == 'Cartography'
        assert contact['country'] == 'Mapland'
        
        # Test layer metadata extraction
        admin_metadata = self.manager._extract_layer_metadata(capabilities, "administrative_boundaries")
        
        assert admin_metadata['title'] == 'Administrative Boundaries'
        assert admin_metadata['abstract'] == 'Administrative Boundaries: Political and administrative boundary data'
        assert admin_metadata['attribution'] == 'National Mapping Agency'
        
        # Test nested layer
        countries_metadata = self.manager._extract_layer_metadata(capabilities, "countries")
        assert countries_metadata['title'] == 'Country Boundaries'
        assert countries_metadata['abstract'] == 'Country Boundaries: International country boundaries'
        
        # Test layer without attribution
        transport_metadata = self.manager._extract_layer_metadata(capabilities, "transportation")
        assert transport_metadata['title'] == 'Transportation Network'
        assert transport_metadata['attribution'] == 'Department of Transportation'