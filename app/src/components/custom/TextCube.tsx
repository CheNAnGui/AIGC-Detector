/**
 * TextCube - 3D Perspective Text Cube
 * A pure CSS 3D text animation inspired by luxury leather craftsmanship.
 * Four faces rotate infinitely, showing alternating AIGC/Human vocabulary.
 */

const WORDS_LINE_1 = ['AIGC', 'Human', 'Synthesized', 'Authentic', 'Digital', 'Organic'];
const WORDS_LINE_2 = ['Neural', 'Natural', 'Generated', 'Created', 'Virtual', 'Tangible'];
const WORDS_LINE_3 = ['Synthetic', 'Genuine', 'Algorithm', 'Intuition', 'Machine', 'Artisan'];
const WORDS_LINE_4 = ['Deepfake', 'Reality', 'Tokenized', 'Written', 'Model', 'Muse'];

const FaceContent = ({ words }: { words: string[] }) => (
  <>
    <span className="gold">{words.join(' & ')}</span>
    <span className="cloned">{words.join(' & ')}</span>
  </>
);

const TextCube = () => {
  return (
    <div className="cube-wrapper">
      <div className="cube-container">
        <div className="cube">
          <div className="line face-1">
            <div className="face">
              <p><FaceContent words={WORDS_LINE_1} /></p>
            </div>
          </div>
          <div className="line face-2">
            <div className="face">
              <p><FaceContent words={WORDS_LINE_2} /></p>
            </div>
          </div>
          <div className="line face-3">
            <div className="face">
              <p><FaceContent words={WORDS_LINE_3} /></p>
            </div>
          </div>
          <div className="line face-4">
            <div className="face">
              <p><FaceContent words={WORDS_LINE_4} /></p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TextCube;
