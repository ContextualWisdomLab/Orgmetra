import '../packages/design-tokens/tokens.css';
import '../apps/hr-workspace/styles.css';

/** @type { import('storybook').Preview } */
const preview = {
  parameters: {
    layout: 'centered',
    controls: { expanded: true }
  },
  decorators: [(story) => `<div class="storybook-preview">${story()}</div>`]
};

export default preview;
