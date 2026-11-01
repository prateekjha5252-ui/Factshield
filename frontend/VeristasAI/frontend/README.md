# FactShield React client utilities

This folder is the React client scaffold. The current complete audit interface in this project is the Streamlit app at `../app.py`.

## Browser-native sentence splitting

`src/utils/sentenceSegmenter.js` uses the browser Internationalization API (`Intl.Segmenter` with `granularity: 'sentence'`) instead of splitting on punctuation. It handles common cases such as `Dr. Smith` and decimal values like `3.14%` more reliably. A conservative fallback is included for older browsers.

Import it in a React text-entry component:

```js
import { splitSentences } from './utils/sentenceSegmenter';
const claims = splitSentences(text);
```

The Streamlit app continues to use the Python analyzer's abbreviation-aware server-side sentence splitter. Do not put provider API keys in React or GitHub Pages source code; call a secured backend instead.
