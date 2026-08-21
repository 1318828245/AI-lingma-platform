<template>
  <main class="alpha-shell">
    <header class="alpha-nav">
      <button class="brand" type="button" @click="router.push('/')"><span aria-hidden="true">↗</span> AI 灵码平台</button>
      <nav aria-label="产品模式">
        <button type="button" @click="router.push('/')">当前版本</button>
        <button class="active" type="button" aria-current="page">Alpha · 数据集成</button>
        <button type="button" @click="router.push('/beta')">Beta · 全栈</button>
      </nav>
      <div class="account"><span>{{ auth.user?.username || '未登录用户' }}</span><button type="button" @click="logout">退出登录</button></div>
    </header>

    <section class="alpha-content">
      <p class="eyebrow"><i /> ALPHA CONCEPT · 尚未开放</p>
      <h1>让前端项目<br />从<span>接口契约</span>开始。</h1>
      <p class="lead">Alpha 版本将把自然语言需求与 OpenAPI、Swagger 或其他数据契约结合，生成可连接真实测试环境的 Vue 前端项目。</p>

      <section class="contract-ribbon" aria-label="Alpha 版本构建流程">
        <article><small>01</small><strong>描述业务</strong><p>说明页面、流程和交互意图。</p></article>
        <b aria-hidden="true">＋</b>
        <article><small>02</small><strong>导入接口契约</strong><p>提供字段、请求、鉴权与错误规则。</p></article>
        <b aria-hidden="true">＝</b>
        <article class="outcome"><small>03</small><strong>真实数据前端</strong><p>生成类型、请求层、状态与页面绑定。</p></article>
      </section>

      <section class="alpha-grid">
        <article class="promise-card"><p class="card-label">ALPHA 的范围</p><h2>不是猜测接口，而是基于契约生成。</h2><ul><li>解析 OpenAPI / Swagger 文档</li><li>生成类型安全的 API Client</li><li>在 Mock 与真实测试数据间切换</li><li>输出可确认的页面—接口—字段绑定清单</li></ul></article>
        <article class="boundary-card"><p class="card-label">当前状态</p><h2>介绍模式</h2><p>数据源导入、密钥管理、真实请求验证和 Alpha 项目创建尚未实现。当前版本的 HTML / Vue demo 生成流程保持不变。</p><button type="button" disabled>即将开放</button></article>
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
.alpha-shell{min-height:100vh;background:#f7f8fc;color:#19264b}.alpha-nav{height:68px;display:grid;grid-template-columns:1fr auto 1fr;align-items:center;padding:0 clamp(20px,4vw,58px);border-bottom:1px solid #dbe1f1;background:rgba(252,253,255,.94);backdrop-filter:blur(16px)}.brand{justify-self:start;border:0;background:transparent;color:#24345f;font:750 18px/1 var(--font-display);cursor:pointer}.brand span{display:inline-grid;place-items:center;width:28px;height:28px;margin-right:8px;border-radius:8px;background:#243b73;color:#d9ffe9;font-size:16px;transform:rotate(-36deg)}nav{display:flex;gap:5px;padding:4px;border:1px solid #dce2f1;border-radius:10px;background:#f2f4fa}nav button{min-height:32px;border:0;border-radius:7px;padding:0 11px;background:transparent;color:#77829c;font-size:12px;font-weight:750;cursor:pointer}nav button.active{background:#fff;color:#265e56;box-shadow:0 2px 6px rgba(39,62,99,.12)}.account{justify-self:end;display:flex;align-items:center;gap:12px;color:#63708c;font-size:13px}.account button{border:0;background:transparent;color:#4056b6;font-weight:700;cursor:pointer}.alpha-content{width:min(1040px,100%);margin:0 auto;padding:clamp(56px,8vw,106px) clamp(20px,5vw,48px) 72px}.eyebrow,.card-label{margin:0;color:#327f71;font:750 11px/1.3 var(--font-mono);letter-spacing:.13em}.eyebrow i{display:inline-block;width:8px;height:8px;margin-right:8px;border-radius:50%;background:#50b59f;box-shadow:0 0 0 5px #dff5ed}.alpha-content h1{max-width:760px;margin:18px 0 18px;color:#1c2b54;font:700 clamp(44px,7vw,82px)/.98 var(--font-display);letter-spacing:-.065em}.alpha-content h1 span{color:#28786a;text-decoration:underline;text-decoration-color:#a9dfd0;text-decoration-thickness:.12em;text-underline-offset:.1em}.lead{max-width:630px;margin:0;color:#65718d;font-size:18px;line-height:1.7}.contract-ribbon{display:grid;grid-template-columns:1fr 34px 1fr 34px 1fr;align-items:stretch;gap:13px;margin:55px 0 22px}.contract-ribbon article{min-height:158px;padding:20px;border:1px solid #d9e0ef;border-radius:14px;background:#fff}.contract-ribbon article small{display:block;margin-bottom:26px;color:#8a96ae;font:700 11px var(--font-mono)}.contract-ribbon strong{display:block;color:#25375f;font-size:16px}.contract-ribbon p{margin:7px 0 0;color:#73809a;font-size:13px;line-height:1.55}.contract-ribbon b{align-self:center;color:#58a894;text-align:center;font-size:22px}.contract-ribbon .outcome{border-color:#9bcebf;background:linear-gradient(145deg,#ecfaf5,#fff)}.alpha-grid{display:grid;grid-template-columns:1.35fr .85fr;gap:18px;margin-top:18px}.promise-card,.boundary-card{min-height:260px;border-radius:16px;padding:27px}.promise-card{background:#253b73;color:#fff;box-shadow:0 20px 40px rgba(34,52,103,.15)}.promise-card .card-label{color:#a9d9cc}.promise-card h2,.boundary-card h2{max-width:440px;margin:11px 0 20px;font:700 28px/1.16 var(--font-display);letter-spacing:-.045em}.promise-card ul{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px 17px;margin:0;padding:0;list-style:none;color:#d8e6ff;font-size:13px}.promise-card li::before{content:'↗';margin-right:7px;color:#9ae5cf}.boundary-card{border:1px dashed #b5c3d9;background:#fbfcff}.boundary-card p:not(.card-label){margin:0;color:#6d7993;font-size:14px;line-height:1.65}.boundary-card button{margin-top:22px;border:1px solid #d6dce9;border-radius:8px;padding:8px 11px;background:#eef1f7;color:#8a95a9;font-size:12px;font-weight:750}.back{display:inline-flex;align-items:center;gap:10px;margin-top:38px;border:0;border-bottom:1px solid #7b8ab2;padding:0 0 5px;background:transparent;color:#314a8e;font-size:14px;font-weight:750;cursor:pointer}.back span{font-size:18px;transition:transform .15s ease}.back:hover span{transform:translateX(4px)}@media(max-width:760px){.alpha-nav{grid-template-columns:1fr auto;height:auto;min-height:64px;gap:10px;padding-block:10px}.alpha-nav nav{order:3;grid-column:1/-1;justify-self:stretch}.alpha-nav nav button{flex:1}.account span{display:none}.contract-ribbon,.alpha-grid{grid-template-columns:1fr}.contract-ribbon b{height:16px}.promise-card ul{grid-template-columns:1fr}.alpha-content{padding-top:58px}}@media(prefers-reduced-motion:reduce){.back span{transition:none}}
</style>
