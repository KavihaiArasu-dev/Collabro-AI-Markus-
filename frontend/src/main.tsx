import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './index.css'

// Filter harmless MediaPipe WebAssembly C++ engine notices from polluting DevTools console
const filterMediaPipeNoise = (originalFn: (...args: any[]) => void) => {
  return (...args: any[]) => {
    if (args.length > 0 && typeof args[0] === 'string') {
      const msg = args[0];
      if (
        msg.includes('gl_context.cc') ||
        msg.includes('OpenGL error checking is disabled') ||
        msg.includes('Graph successfully started running')
      ) {
        return;
      }
    }
    originalFn.apply(console, args);
  };
};

console.warn = filterMediaPipeNoise(console.warn);
console.error = filterMediaPipeNoise(console.error);
console.log = filterMediaPipeNoise(console.log);
console.info = filterMediaPipeNoise(console.info);

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
