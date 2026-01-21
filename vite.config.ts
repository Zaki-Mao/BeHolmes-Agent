import { defineConfig } from 'vite'  
export default defineConfig({  
  server: {  
    allowedHosts: [  
      'beholmes.zeabur.app',  
      'localhost',  
      '127.0.0.1',  
      '.zeabur.app'  
    ]  
  }  
})  
