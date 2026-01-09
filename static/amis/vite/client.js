import { hmrClientUrl, parseQuery, withLeadingSlash, withoutTrailingSlash } from './utils.js'
import { nanoid } from './nanoid.js'

let socketProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
let socketHost = `${window.location.hostname}:${window.location.port || (window.location.protocol === 'https:' ? '443' : '80')}`
let socket = new WebSocket(`${socketProtocol}://${socketHost}`, 'vite-hmr')
let messageBuffer = []
let lastUpdateId = null

function send(message) {
  if (socket.readyState === 1) {
    socket.send(JSON.stringify(message))
  } else {
    messageBuffer.push(message)
  }
}

socket.addEventListener('open', () => {
  messageBuffer.forEach((msg) => {
    socket.send(JSON.stringify(msg))
  })
  messageBuffer = []
})

socket.addEventListener('message', async (msg) => {
  const data = msg.data
  try {
    const payload = JSON.parse(data)
    if (payload.type === 'connected') {
      console.log('[vite] connected.')
    } else if (payload.type === 'update') {
      await payloadHandler(payload)
    } else if (payload.type === 'custom') {
      customEventHandler(payload)
    } else if (payload.type === 'full-reload') {
      window.location.reload()
    } else if (payload.type === 'prune') {
      import.meta.modules.forEach((mod) => {
        if (mod.consumed && !mod.isSelfAccepted) {
          mod.dispose()
        }
      })
    }
  } catch (error) {
    console.error(`[vite] error while handling message: ${error.message}\n`, data)
  }
})

async function payloadHandler(payload) {
  if (payload.id === lastUpdateId) {
    return
  }
  lastUpdateId = payload.id

  const updates = payload.updates || []
  for (const update of updates) {
    await applyUpdate(update)
  }
}

async function applyUpdate(update) {
  const { path, change, acceptedPath, timestamp } = update
  const mod = import.meta.modules.find((mod) => mod.file === path)

  if (!mod) {
    return
  }

  if (change && (change.type === 'js' || change.type === 'css')) {
    const importSpecifier = mod.imports.find((imp) => imp.specifier === path)
    if (importSpecifier) {
      const dep = import.meta.modules.find((mod) => mod.file === importSpecifier.partialUrl)
      if (dep) {
        dep.refresh()
      }
    }
  }

  if (mod && mod.hot) {
    const isSelfUpdate = path === mod.file
    if (isSelfUpdate) {
      const data = { ...mod.hot.data }
      mod.dispose()
      const newMod = await import(acceptedPath + '?t=' + timestamp)
      mod.callbacks = newMod.callbacks || []
      mod.hot = {
        ...newMod.hot,
        data
      }
      mod.imports = newMod.imports || []
      if (!mod.isSelfAccepted) {
        window.location.reload()
        return
      }
    } else {
      mod.hot.invalidate('self')
    }
  }
}

function customEventHandler(payload) {
  const eventName = payload.event
  const data = payload.data
  if (eventName === 'vite:preload-error') {
    window.addEventListener('vite:preload-error', (e) => {
      e.detail.error = data.error
    })
  }
  const handlers = import.meta.hot.acceptedEvents[eventName]
  if (handlers) {
    handlers.forEach((handler) => handler(data))
  }
}

function createHotContext(hot) {
  return {
    get data() {
      return hot.data
    },
    accept(deps, callback) {
      if (typeof deps === 'string') {
        deps = [deps]
      }
      hot.acceptedDependencies = deps
      if (callback) {
        hot.acceptCallbacks.push(callback)
      }
    },
    acceptDeps(deps, callback) {
      this.accept(deps, callback)
    },
    acceptSelf(cb) {
      hot.acceptSelfCb = cb
    },
    dispose(cb) {
      hot.disposeCallbacks.push(cb)
    },
    decline() {
      hot.isDeclined = true
    },
    invalidate(message) {
      console.warn(`[vite] hot invalidation: ${message}`)
      send({
        type: 'custom',
        event: 'vite:invalidate',
        data: { path: hot.file, message }
      })
    },
    on(event, cb) {
      hot.acceptedEvents[event] = hot.acceptedEvents[event] || []
      hot.acceptedEvents[event].push(cb)
    },
    send(event, data) {
      send({
        type: 'custom',
        event: `vite:${event}`,
        data
      })
    }
  }
}

function getHotModules() {
  return window.__vite_modules__ || {}
}

function createHotModules() {
  window.__vite_modules__ = {}
  return window.__vite_modules__
}

function createImportMetaUtils() {
  return {
    url: window.location.href,
    resolve: async (id, parentPath) => {
      return withLeadingSlash(withoutTrailingSlash(parentPath)) + '/' + id
    },
    modules: import.meta.modules
  }
}

export {
  createHotContext,
  createHotModules,
  createImportMetaUtils,
  getHotModules,
  send
}
