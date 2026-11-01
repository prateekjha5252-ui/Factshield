/** Browser-native sentence segmentation using the Internationalization API.
 * Intl.Segmenter handles common abbreviations and decimal numbers more reliably
 * than splitting on punctuation with a regular expression.
 */
export function splitSentences(text, locale = (typeof navigator !== 'undefined' && navigator.language) || 'en') {
  if (!text || !text.trim()) return [];
  if (typeof Intl !== 'undefined' && typeof Intl.Segmenter === 'function') {
    const segmenter = new Intl.Segmenter(locale, { granularity: 'sentence' });
    return Array.from(segmenter.segment(text), part => part.segment.trim()).filter(Boolean);
  }
  // Compatibility fallback for older browsers; protects common abbreviations
  // and decimal points before splitting.
  const protectedText = text
    .replace(/\b(Dr|Mr|Mrs|Ms|Prof|Sr|Jr|vs|etc|e\.g|i\.e)\./gi, '$1<prd>')
    .replace(/(\d)\.(\d)/g, '$1<decimal>$2');
  return protectedText.split(/(?<=[.!?…])\s+|\n+/)
    .map(s => s.replace(/<prd>/g, '.').replace(/<decimal>/g, '.').trim())
    .filter(Boolean);
}
