/** @type { import('@storybook/web-components-vite').StorybookConfig } */
const config = {
  stories: ['../apps/hr-workspace/**/*.stories.@(js|mjs)'],
  framework: '@storybook/web-components-vite',
  docs: { autodocs: 'tag' }
};

export default config;
