import { createApp } from "vue";
import { createPinia } from "pinia";
import { ElButton, ElInput } from "element-plus";
import "element-plus/es/components/button/style/css";
import "element-plus/es/components/input/style/css";
import "element-plus/es/components/message/style/css";
import "element-plus/es/components/message-box/style/css";
import "@fontsource/space-grotesk/latin-500.css";
import "@fontsource/space-grotesk/latin-600.css";
import "@fontsource/ibm-plex-mono/latin-400.css";
import "@fontsource/ibm-plex-mono/latin-500.css";
import "@fontsource/inter/latin-400.css";
import "@fontsource/inter/latin-500.css";
import "@fontsource/inter/latin-600.css";

import App from "./App.vue";
import router from "./router";
import "./styles/global.css";

createApp(App)
  .use(createPinia())
  .use(router)
  .component("ElButton", ElButton)
  .component("ElInput", ElInput)
  .mount("#app");
