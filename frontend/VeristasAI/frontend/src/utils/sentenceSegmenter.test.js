import { splitSentences } from './sentenceSegmenter';

test('keeps abbreviations and decimals inside the correct sentence', () => {
  expect(splitSentences('Dr. Smith measured 3.14%. It was recorded.'))
    .toEqual(['Dr. Smith measured 3.14%.', 'It was recorded.']);
});
