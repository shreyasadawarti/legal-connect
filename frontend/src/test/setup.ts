import '@testing-library/jest-dom'

if (!window.matchMedia) {
  window.matchMedia = (query: string) =>
    ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => undefined,
      removeListener: () => undefined,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      dispatchEvent: () => false,
    }) as MediaQueryList
}

// jsdom implements neither of these, and the profile picture preview relies on
// them for its local object URL.
if (!URL.createObjectURL) {
  URL.createObjectURL = () => 'blob:mock-object-url'
}
if (!URL.revokeObjectURL) {
  URL.revokeObjectURL = () => undefined
}

// jsdom has no layout engine, so scroll containers used for auto-scrolling to the
// latest message do not implement scrollTo.
if (!Element.prototype.scrollTo) {
  Element.prototype.scrollTo = () => undefined
}
