import { Server } from '@hocuspocus/server'
import { Logger } from '@hocuspocus/extension-logger'
import crypto from 'crypto'

// Helper to sanitize document name for logging
function sanitizeDocumentName(name) {
  // Hash the document name for privacy
  const hash = crypto.createHash('sha256').update(name).digest('hex').substring(0, 8)
  return `doc-${hash}`
}

const server = Server.configure({
  port: 1234,
  
  extensions: [
    new Logger(),
  ],

  async onConnect(data) {
    console.log(`Client connected to document: ${sanitizeDocumentName(data.documentName)}`)
  },

  async onDisconnect(data) {
    console.log(`Client disconnected from document: ${sanitizeDocumentName(data.documentName)}`)
  },

  async onChange(data) {
    console.log(`Document ${sanitizeDocumentName(data.documentName)} changed`)
  }
})

server.listen()
console.log('Hocuspocus server running on port 1234 (http://localhost:1234)')
