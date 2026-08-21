<template>
  <main class="beta-shell">
    <header class="beta-nav">
      <button class="brand" type="button" @click="router.push('/')"><span aria-hidden="true">◆</span> AI 灵码平台</button>
      <nav aria-label="产品模式">
        <button type="button" @click="router.push('/')">当前版本</button>
        <button type="button" @click="router.push('/alpha')">Alpha · 数据集成</button>
        <button class="active" type="button" aria-current="page">Beta · 全栈</button>
      </nav>
      <div class="account"><span>{{ auth.user?.username || '未登录用户' }}</span><button type="button" @click="logout">退出登录</button></div>
    </header>

    <section class="beta-content">
      <p class="eyebrow"><i /> BETA CONCEPT · 尚未开放</p>
      <h1>从界面到服务，<br />交付一套<span>可运行的系统</span>。</h1>
      <p class="lead">Beta 版本探索全栈应用生成：自然语言定义业务目标，平台将协助产出前端、数据模型、受控后端服务、鉴权和部署交付物。</p>

      <section class="system-blueprint" aria-label="Beta 全栈交付蓝图">
        <div class="blueprint-head"><span>APPLICATION BLUEPRINT</span><b>完整应用由可审查模块组成</b></div>
        <div class="blueprint-layers">
          <article><small>体验层</small><strong>Vue 前端</strong><p>页面、交互、状态与错误反馈</p></article>
          <article><small>服务层</small><strong>受控 API</strong><p>鉴权、业务规则与接口边界</p></article>
          <article><small>数据层</small><strong>数据库模型</strong><p>迁移、权限和可追溯数据</p></article>
          <article><small>交付层</small><strong>部署与运维</strong><p>环境、日志、备份与发布</p></article>
        </div>
      </section>

      <section class="beta-grid">
        <article class="guardrail-card"><p class="card-label">BETA 的原则</p><h2>全栈不等于让模型随意运行后端。</h2><p>每项交付必须有结构化规格、受控执行环境、数据库迁移、权限校验、测试证据和人工审批。业务语义不明确时，系统必须停下来要求确认。</p></article>
        <article class="status-card"><p class="card-label">当前状态</p><h2>介绍模式</h2><ul><li>尚未生成后端服务或数据库</li><li>尚未提供密钥、鉴权或部署托管</li><li>不会影响当前 demo 或 Alpha 入口</li></ul><button type="button" disabled>即将开放</button></article>
      </section>

      <button class="back" type="button" @click="router.push('/')">返回当前 demo 生成模式 <span>→</span></button>
    </section>
  </main>
</template>

<script setup lang="ts">
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";

const router = useRouter();
const auth = useAuthStore();
function logout() { auth.logout(); router.push("/login"); }
</script>

<style scoped>
.beta-shell{min-height:100vh;background:#11182b;color:#edf2ff}.beta-nav{height:68px;display:grid;grid-template-columns:1fr auto 1fr;align-items:center;padding:0 clamp(20px,4vw,58px);border-bottom:1px solid rgba(155,174,223,.2);background:rgba(15,22,40,.91);backdrop-filter:blur(16px)}.brand{justify-self:start;border:0;background:transparent;color:#f1f5ff;font:750 18px/1 var(--font-display);cursor:pointer}.brand span{display:inline-grid;place-items:center;width:28px;height:28px;margin-right:8px;border-radius:8px;background:#efb85b;color:#18213a;font-size:13px}.beta-nav nav{display:flex;gap:5px;padding:4px;border:1px solid rgba(155,174,223,.18);border-radius:10px;background:rgba(49,64,103,.4)}.beta-nav nav button{min-height:32px;border:0;border-radius:7px;padding:0 11px;background:transparent;color:#aab8d9;font-size:12px;font-weight:750;cursor:pointer}.beta-nav nav button.active{background:#f6c56e;color:#28324a;box-shadow:0 2px 8px rgba(0,0,0,.2)}.account{justify-self:end;display:flex;align-items:center;gap:12px;color:#aab8d9;font-size:13px}.account button{border:0;background:transparent;color:#f4c46c;font-weight:700;cursor:pointer}.beta-content{width:min(1040px,100%);margin:0 auto;padding:clamp(56px,8vw,106px) clamp(20px,5vw,48px) 72px}.eyebrow,.card-label{margin:0;color:#f1bd62;font:750 11px/1.3 var(--font-mono);letter-spacing:.13em}.eyebrow i{display:inline-block;width:8px;height:8px;margin-right:8px;transform:rotate(45deg);background:#f3be60;box-shadow:0 0 0 5px rgba(243,190,96,.14)}.beta-content h1{max-width:850px;margin:18px 0;color:#f5f7ff;font:700 clamp(43px,7vw,80px)/.98 var(--font-display);letter-spacing:-.065em}.beta-content h1 span{color:#f4c46c}.lead{max-width:670px;margin:0;color:#b8c4e0;font-size:18px;line-height:1.7}.system-blueprint{overflow:hidden;margin-top:54px;border:1px solid rgba(155,174,223,.3);border-radius:16px;background:#17213b;box-shadow:0 26px 56px rgba(0,0,0,.2)}.blueprint-head{display:flex;align-items:center;justify-content:space-between;padding:16px 20px;border-bottom:1px solid rgba(155,174,223,.2);color:#f4c46c;font:700 11px var(--font-mono);letter-spacing:.11em}.blueprint-head b{color:#b4c1df;font:600 12px var(--font-body);letter-spacing:0}.blueprint-layers{display:grid;grid-template-columns:repeat(4,1fr)}.blueprint-layers article{min-height:176px;padding:22px;border-right:1px solid rgba(155,174,223,.2)}.blueprint-layers article:last-child{border-right:0;background:rgba(243,190,96,.07)}.blueprint-layers small{display:block;margin-bottom:30px;color:#7f91bd;font:700 11px var(--font-mono)}.blueprint-layers strong{display:block;color:#f4f7ff;font-size:17px}.blueprint-layers p{margin:8px 0 0;color:#aab8d5;font-size:13px;line-height:1.55}.beta-grid{display:grid;grid-template-columns:1.25fr .95fr;gap:18px;margin-top:18px}.guardrail-card,.status-card{min-height:254px;border-radius:16px;padding:27px}.guardrail-card{background:#f4c46c;color:#1d2740}.guardrail-card .card-label{color:#715520}.guardrail-card h2,.status-card h2{margin:11px 0 17px;font:700 28px/1.16 var(--font-display);letter-spacing:-.045em}.guardrail-card p:not(.card-label){max-width:530px;margin:0;color:#46536e;font-size:14px;line-height:1.7}.status-card{border:1px dashed rgba(155,174,223,.47);background:rgba(35,48,81,.46)}.status-card ul{display:grid;gap:8px;margin:0;padding:0;list-style:none;color:#bbc7e0;font-size:13px}.status-card li::before{content:'—';margin-right:7px;color:#f4c46c}.status-card button{margin-top:20px;border:1px solid rgba(170,184,217,.28);border-radius:8px;padding:8px 11px;background:rgba(147,163,201,.12);color:#91a1c4;font-size:12px;font-weight:750}.back{display:inline-flex;align-items:center;gap:10px;margin-top:38px;border:0;border-bottom:1px solid #8294be;padding:0 0 5px;background:transparent;color:#e9c57e;font-size:14px;font-weight:750;cursor:pointer}.back span{font-size:18px;transition:transform .15s ease}.back:hover span{transform:translateX(4px)}@media(max-width:760px){.beta-nav{grid-template-columns:1fr auto;height:auto;min-height:64px;gap:10px;padding-block:10px}.beta-nav nav{order:3;grid-column:1/-1;justify-self:stretch}.beta-nav nav button{flex:1;padding-inline:6px;font-size:11px}.account span{display:none}.blueprint-layers,.beta-grid{grid-template-columns:1fr}.blueprint-layers article{min-height:auto;border-right:0;border-bottom:1px solid rgba(155,174,223,.2)}.blueprint-layers article:last-child{border-bottom:0}.blueprint-layers small{margin-bottom:12px}.beta-content{padding-top:58px}}@media(prefers-reduced-motion:reduce){.back span{transition:none}}
</style>
