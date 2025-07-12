/**
 * Test setup configuration
 */
import '@testing-library/jest-dom';
import { vi } from 'vitest';

// Mock IntersectionObserver
global.IntersectionObserver = vi.fn(() => ({
  observe: vi.fn(),
  disconnect: vi.fn(),
  unobserve: vi.fn(),
}));

// Mock ResizeObserver
global.ResizeObserver = vi.fn(() => ({
  observe: vi.fn(),
  disconnect: vi.fn(),
  unobserve: vi.fn(),
}));

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(), // deprecated
    removeListener: vi.fn(), // deprecated
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};
global.localStorage = localStorageMock;

// Mock sessionStorage
const sessionStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};
global.sessionStorage = sessionStorageMock;

// Mock window.location
delete (window as any).location;
window.location = {
  ...window.location,
  href: 'http://localhost:3000',
  origin: 'http://localhost:3000',
  pathname: '/',
  search: '',
  hash: '',
  assign: vi.fn(),
  replace: vi.fn(),
  reload: vi.fn(),
};

// Mock Monaco Editor
vi.mock('monaco-editor', () => ({
  editor: {
    create: vi.fn(() => ({
      getValue: vi.fn(),
      setValue: vi.fn(),
      dispose: vi.fn(),
      onDidChangeModelContent: vi.fn(),
      addCommand: vi.fn(),
      trigger: vi.fn(),
      getModel: vi.fn(() => ({
        getValueInRange: vi.fn(),
        getOffsetAt: vi.fn(),
      })),
    })),
    setTheme: vi.fn(),
  },
  languages: {
    registerCompletionItemProvider: vi.fn(),
    registerCodeActionProvider: vi.fn(),
    CompletionItemKind: {
      Snippet: 27,
    },
    CompletionItemInsertTextRule: {
      InsertAsSnippet: 4,
    },
    CompletionTriggerKind: {
      TriggerCharacter: 1,
      Invoke: 0,
    },
  },
  KeyMod: {
    CtrlCmd: 2048,
  },
  KeyCode: {
    KeyI: 39,
  },
  Range: vi.fn(),
}));

// Mock React Markdown
vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => <div>{children}</div>,
}));

// Mock Syntax Highlighter
vi.mock('react-syntax-highlighter', () => ({
  Prism: ({ children }: { children: string }) => <pre>{children}</pre>,
}));

vi.mock('react-syntax-highlighter/dist/cjs/styles/prism', () => ({
  vscDarkPlus: {},
}));

// Increase timeout for async tests
vi.setConfig({
  testTimeout: 10000,
});