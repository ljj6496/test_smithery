const fs = require('fs');
const path = require('path');

// Create .smithery directory
fs.mkdirSync('.smithery', { recursive: true });

// Read smithery.yaml to extract config
const manifest = {
  name: 'kis-symbol-search',
  version: '1.0.0',
  description: '종목코드 검색 MCP Server',
  runtime: 'container',
  build: {
    dockerfile: 'Dockerfile',
    context: '.'
  },
  transport: {
    type: 'http',
    port: 8000
  },
  configSchema: {
    type: 'object',
    properties: {
      dataDir: {
        type: 'string',
        description: 'Directory for master files and data storage'
      }
    }
  }
};

fs.writeFileSync('.smithery/manifest.json', JSON.stringify(manifest, null, 2));
console.log('Manifest created:', JSON.stringify(manifest, null, 2));
