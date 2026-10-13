/**
 * Moves focus to the first control that failed validation, so keyboard and screen
 * reader users land on the problem instead of hunting for the inline message.
 *
 * Error keys may be nested (`nutrition.calories`); the input name is the last segment.
 */
export function focusFirstInvalidField(
  form: HTMLFormElement | null,
  errorKeys: string[],
): void {
  if (!form) return;
  for (const key of errorKeys) {
    const control = form.elements.namedItem(key.split(".").at(-1) ?? key);
    const target = control instanceof RadioNodeList ? control[0] : control;
    if (target instanceof HTMLElement) {
      target.focus();
      return;
    }
  }
}
