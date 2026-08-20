<template>
  <router-view :key="String($route.params.id ?? $route.name)" />
</template>
