import { Server } from '@hocuspocus/server'
import { Logger } from '@hocuspocus/extension-logger'

const server = Server.configure({
  port: 1234,
  
  extensions: [
    new Logger(),
  ],

  async onConnect(data) {
    console.log(`Client connected to document: ${data.documentName}`)
  },

  async onDisconnect(data) {
    console.log(`Client disconnected from document: ${data.documentName}`)
  },

  async onChange(data) {
    console.log(`Document ${data.documentName} changed`)
  }
})

server.listen()
console.log('Hocuspocus server running on port 1234')
