import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "../stores/auth";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/login",
      name: "login",
      component: () => import("../views/LoginView.vue"),
    },
    {
      path: "/",
      name: "projects",
      component: () => import("../views/ProjectListView.vue"),
    },
    { path: "/admin", name: "admin", component: () => import("../views/AdminDashboardView.vue") },
    {
      path: "/projects/:id",
      name: "generation",
      component: () => import("../views/GenerationChatView.vue"),
      props: true,
    },
    {
      path: "/projects/:id/preview",
      name: "preview",
      component: () => import("../views/PreviewWorkspaceView.vue"),
      props: true,
    },
  ],
});

router.beforeEach((to) => {
  const auth = useAuthStore();
  if (to.name !== "login" && !auth.isLoggedIn) {
    return { name: "login" };
  }
  if (to.name === "login" && auth.isLoggedIn) {
    return { name: "projects" };
  }
  if (to.name === "admin" && auth.user?.role !== "admin") return { name: "projects" };
});

export default router;
