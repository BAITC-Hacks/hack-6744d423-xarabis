export function createAutomaticAnalysis<T>() {
  const requests = new Map<string, Promise<T>>();
  return {run(key: string, request: () => Promise<T>): Promise<T> {
    let pending = requests.get(key);
    if (!pending) {
      pending = Promise.resolve().then(request);
      requests.set(key, pending);
    }
    return pending;
  }};
}

const scenarioAutomaticAnalysis = createAutomaticAnalysis<void>();
export function getScenarioAutomaticAnalysis() {
  return scenarioAutomaticAnalysis;
}
