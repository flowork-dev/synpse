//#######################################################################
//# WEBSITE https://flowork.cloud
//# File NAME : C:\FLOWORK\docs\.vitepress\config.mjs
//# CATATAN: (PERBAIKAN) Mengganti link GitHub ke repo baru.
//#######################################################################
import { defineConfig } from 'vitepress'

export default defineConfig({
  title: "Flowork Docs",
  description: "Flowork - Developer Documentation & Guides",
  base: '/',

  themeConfig: {
    // (CATATAN) Pastikan file logo ini ada di C:\FLOWORK\docs\public\favicon.svg
    // Jika tidak, hapus baris logo ini.
    logo: '/favicon.svg',
    nav: [
      { text: 'Guide', link: '/guide/what-is-flowork' }, // English Hardcode
      { text: 'API Reference', link: '/api/introduction' }, // English Hardcode
      { text: 'flowork.cloud', link: 'https://flowork.cloud' } // English Hardcode
    ],

    sidebar: {
      '/guide/': [
        {
          text: 'Introduction', // English Hardcode
          items: [
            { text: 'What is Flowork?', link: '/guide/what-is-flowork' }, // English Hardcode
            { text: 'Installation', link: '/guide/installation' }, // English Hardcode
            { text: 'Quick Start', link: '/guide/quick-start' } // English Hardcode
          ]
        }
      ],
      '/api/': [
        {
          text: 'API Reference', // English Hardcode
          items: [
            { text: 'Introduction', link: '/api/introduction' }, // English Hardcode
            { text: 'Gateway API', link: '/api/gateway-api' }, // English Hardcode
            { text: 'Engine WebSocket', link: '/api/engine-websocket' } // English Hardcode
          ]
        }
      ]
    },

    socialLinks: [
      // --- (PERBAIKAN) ---
      { icon: 'github', link: 'https://github.com/flowork-dev/flowork-platform' }
      // --- (AKHIR PERBAIKAN) ---
    ],

    footer: {
      message: 'Released under the MIT License.', // English Hardcode
      copyright: 'Copyright © 2024-present Flowork' // English Hardcode
    }
  }
})