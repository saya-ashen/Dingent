// Framework-agnostic navigation hook
export interface NavigationContextType {
  navigate: (url: string) => void;
}

let navigationImplementation: NavigationContextType | null = null;

export function setNavigationImplementation(impl: NavigationContextType) {
  navigationImplementation = impl;
}

export function useNavigation(): NavigationContextType {
  if (!navigationImplementation) {
    throw new Error(
      'Navigation implementation not set. Please call setNavigationImplementation in your app setup.'
    );
  }
  return navigationImplementation;
}