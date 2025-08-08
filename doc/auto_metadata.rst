Auto Metadata
=============

MapProxy can automatically inherit metadata from WMS sources, eliminating the need to manually configure layer metadata. This feature fetches metadata from WMS GetCapabilities documents and integrates it seamlessly into your MapProxy configuration.

Overview
--------

The auto metadata feature provides layer-level automatic metadata inheritance:

**Layer-level auto metadata**: Individual layers inherit metadata from their WMS sources

Manual configuration always takes priority over automatically inherited metadata.

Configuration
-------------

Layer-Level Auto Metadata
~~~~~~~~~~~~~~~~~~~~~~~~~~

Enable auto metadata for individual layers by adding ``auto_metadata: true`` to the layer's metadata section:

.. code-block:: yaml

    layers:
      - name: streets
        title: Street Map
        sources: [streets_cache]
        md:
          auto_metadata: true
          title: "Custom Layer Title"  # Manual config takes priority

When enabled, MapProxy will:

1. Traverse the layer's sources to find underlying WMS sources
2. Fetch GetCapabilities documents from WMS sources
3. Extract and merge metadata from matching layers
4. Apply the metadata to the layer configuration

Metadata Fields
---------------

Layer Metadata Fields
~~~~~~~~~~~~~~~~~~~~~~

The following metadata fields are automatically inherited from WMS sources:

- ``title`` - Layer title from WMS GetCapabilities
- ``abstract`` - Layer description with automatic title prepending
- ``attribution`` - Layer attribution information
- ``contact`` - Layer contact information (person, organization, email, phone, etc.)

**Abstract Field Processing**: When both title and abstract are available from the WMS source, the abstract field is automatically enhanced by prepending the title: ``"Layer Title: Original Abstract"``. This improves readability and provides better context.

Layer Matching
---------------

For layers with multiple or complex source configurations, MapProxy uses intelligent layer matching:

Source Specification Format
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can specify which WMS layer to use for metadata using the format: ``source_name:layer_name``

.. code-block:: yaml

    layers:
      - name: cadastral
        sources: [cadastral_cache]
        md:
          auto_metadata: true

    sources:
      cadastral_wms:
        type: wms
        req:
          url: https://example.com/wms
          layers: cadastral_parcels  # This layer name will be used for metadata

For complex layer specifications like ``source_lhm_plan:plan:g_fnp``, the last segment (``g_fnp``) is used as the target layer name.

Layer Matching Strategies
~~~~~~~~~~~~~~~~~~~~~~~~~~

MapProxy uses the following matching strategies in order of preference:

1. **Exact match**: Layer name matches exactly
2. **Case-insensitive match**: Layer name matches ignoring case
3. **Partial match**: Layer name contains the target as a substring

Authentication
--------------

Auto metadata supports the same authentication methods as regular WMS sources:

HTTP Basic Authentication
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    sources:
      protected_wms:
        type: wms
        req:
          url: https://example.com/wms
          layers: protected_layer
        http:
          username: user
          password: secret

HTTP Headers Authentication
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    sources:
      api_wms:
        type: wms
        req:
          url: https://example.com/wms
          layers: api_layer
        http:
          headers:
            Authorization: "Bearer token123"
            X-API-Key: "key456"

URL-Embedded Credentials
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    sources:
      embedded_auth_wms:
        type: wms
        req:
          url: https://user:pass@example.com/wms
          layers: layer_name

The same credentials used for tile requests are automatically used for metadata fetching.

Complete Examples
-----------------

Basic Layer Auto Metadata
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    layers:
      - name: roads
        title: Road Network
        sources: [roads_cache]
        md:
          auto_metadata: true

    caches:
      roads_cache:
        sources: [roads_wms]

    sources:
      roads_wms:
        type: wms
        req:
          url: https://maps.example.com/wms
          layers: road_network

Multi-Source Layer with Authentication
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    layers:
      - name: combined_map
        sources: [public_cache, private_cache]
        md:
          auto_metadata: true
          title: "Combined Public and Private Data"  # Manual override

    caches:
      public_cache:
        sources: [public_wms]
      private_cache:
        sources: [private_wms]

    sources:
      public_wms:
        type: wms
        req:
          url: https://public.example.com/wms
          layers: public_layer

      private_wms:
        type: wms
        req:
          url: https://private.example.com/wms
          layers: private_layer
        http:
          username: user
          password: secret

Priority and Merging
--------------------

Configuration Priority
~~~~~~~~~~~~~~~~~~~~~~~

Manual configuration always takes priority over auto metadata:

1. **Manual configuration** (highest priority)
2. **Auto metadata from WMS sources**
3. **MapProxy defaults** (lowest priority)

Multi-Source Merging
~~~~~~~~~~~~~~~~~~~~~

When a layer has multiple WMS sources, metadata is merged using these rules:

- **String fields**: First non-empty value is used
- **Contact information**: Fields are merged, manual config takes priority

Error Handling
--------------

Auto metadata includes robust error handling:

- **Network errors**: Failed GetCapabilities requests are logged but don't prevent startup
- **Parsing errors**: Invalid XML responses are handled gracefully
- **Missing layers**: Layers not found in WMS sources are logged as warnings
- **Authentication failures**: Auth errors are logged with suggestions

Performance Considerations
--------------------------

- **Startup impact**: GetCapabilities requests are made during configuration loading
- **Caching**: Metadata is cached in memory to prevent repeated requests
- **Timeout handling**: Network requests have reasonable timeouts to prevent blocking
- **Concurrent requests**: Multiple WMS sources are queried efficiently

Best Practices
--------------

1. **Use caching**: Always use caches between layers and WMS sources for better performance
2. **Manual overrides**: Use manual configuration for critical metadata fields
3. **Authentication**: Ensure WMS credentials have GetCapabilities permissions
4. **Network reliability**: Consider network latency when using many remote WMS sources
5. **Testing**: Test auto metadata with your WMS sources before production deployment

Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~

**"No metadata found for layer"**
  - Check that the WMS source is reachable
  - Verify the layer name exists in the WMS GetCapabilities
  - Ensure authentication credentials are correct

**"GetCapabilities request failed"**
  - Check network connectivity to the WMS server
  - Verify the WMS URL is correct
  - Check authentication credentials and permissions

**"Layer name not found in WMS source"**
  - Verify the layer name in the WMS GetCapabilities document
  - Check for case sensitivity issues
  - Use the source specification format: ``source_name:layer_name``

Debugging
~~~~~~~~~

Enable debug logging to troubleshoot auto metadata issues:

.. code-block:: bash

    mapproxy-util serve-develop mapproxy.yaml --debug

This will show detailed information about:
- GetCapabilities requests and responses
- Layer matching attempts
- Metadata extraction and merging
- Authentication processes

Migration from Manual Configuration
-----------------------------------

To migrate existing manual metadata to auto metadata:

1. **Backup your configuration**: Always backup before making changes
2. **Enable auto metadata**: Add ``auto_metadata: true`` to relevant sections
3. **Remove redundant fields**: Remove metadata that will be inherited automatically
4. **Keep important overrides**: Maintain manual configuration for critical fields
5. **Test thoroughly**: Verify that auto metadata produces expected results

Example migration:

**Before:**

.. code-block:: yaml

    layers:
      - name: parcels
        sources: [parcels_cache]
        md:
          title: "Cadastral Parcels"
          abstract: "Property boundary information"
          contact:
            person: "GIS Administrator"
            organization: "City Planning"

**After:**

.. code-block:: yaml

    layers:
      - name: parcels
        sources: [parcels_cache]
        md:
          auto_metadata: true
          contact:
            organization: "City Planning"  # Keep important overrides