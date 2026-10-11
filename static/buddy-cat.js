// <buddy-cat> — the user's pixel cat as a living stage.
// attrs: mode = auto|sit|front|tall|groom|sleep|alert|wave|walk · scale (2) · height (150) · start (0..1) · floor (line|none) · base ("sprites/")
//        cue = "action:n" — a change plays celebrate|jump|alert|stretch|wake, then the cat goes back to its mode.
// Motion: every action is a queue of steps (pose holds, frame loops, moves). Walk/run/stroll frames advance by distance
// travelled, so paws stay planted while the cat speeds up and slows down; holds are jittered so nothing loops mechanically.
(function(){
  if (customElements.get('buddy-cat')) return;
  var GAIT = {
    stroll:{frames:['walkalt_0','walkalt_1','walkalt_2','walkalt_3','walkalt_4','walkalt_5'], stride:.42, vmax:.55},
    walk:{frames:['walk_0','walk_1','walk_2','walk_3','walk_4','walk_5','walk_6','walk_7'], stride:.55, vmax:1},
    run:{frames:['run_0','run_1','run_2','run_3'], stride:.95, vmax:2.3}
  };
  var BLINK = {sit_side:1,sit_front:1,sit_tall:1,sit_droopy:1,groom_0:1};
  var ALL = ['walkalt_0','walkalt_1','walkalt_2','walkalt_3','walkalt_4','walkalt_5','walk_0','walk_1','walk_2','walk_3','walk_4','walk_5','walk_6','walk_7',
    'run_0','run_1','run_2','run_3','jump_0','jump_1','jump_2','jump_3','jump_4','jump_5','groom_0','groom_1','groom_2','groom_3','groom_4',
    'sit_side','sit_front','sit_tall','sit_droopy','loaf','curl','ball','peek_a','peek_b','stretch','wave'];
  var CSS = ':host{display:block;position:relative;overflow:hidden;user-select:none;cursor:pointer}'+
    '.floor{position:absolute;left:0;right:0;bottom:18px;height:1px;background:var(--color-divider,rgba(0,0,0,.16))}'+
    '.cat{position:absolute;bottom:18px;left:0;will-change:transform;pointer-events:none}'+
    '.body{width:100%;height:100%;transform-origin:50% 100%}'+
    'img{width:100%;height:100%;image-rendering:pixelated;display:block;filter:drop-shadow(0 4px 3px rgba(0,0,0,.18))}'+
    '.flip .body{transform:scaleX(-1)}'+
    '.breath .body{animation:br 3.4s ease-in-out infinite}.breath.flip .body{animation:brf 3.4s ease-in-out infinite}'+
    '@keyframes br{50%{transform:scale(1.03,.97)}}@keyframes brf{0%,100%{transform:scaleX(-1)}50%{transform:scaleX(-1) scale(1.03,.97)}}'+
    '.fx{position:absolute;bottom:18px;left:0;pointer-events:none;font-family:var(--font-heading,serif);font-style:italic}'+
    '.fx span{position:absolute;left:64%;opacity:0}'+
    '.zzz{font-size:18px;color:var(--color-neutral-600,#777)}.bang{font-size:28px;font-style:normal;font-weight:600;color:var(--color-accent-700,#7d5411)}'+
    '.fx[data-fx=sleep] .zzz{animation:zz 3.4s ease-in infinite}.fx[data-fx=alert] .bang{animation:bp .9s ease-in-out infinite}'+
    '@keyframes zz{0%{opacity:0;transform:scale(.65)}18%{opacity:.95}75%{opacity:.6}100%{opacity:0;transform:translate(20px,-40px) scale(1.15)}}'+
    '@keyframes bp{0%,100%{opacity:.9}50%{opacity:1;transform:translateY(-7px) scale(1.16)}}'+
    '.conf{position:absolute;inset:0;pointer-events:none}.conf i{position:absolute;width:4px;height:8px;border-radius:1px;opacity:0;animation:cb 1.1s ease-out 1}'+
    '@keyframes cb{0%{opacity:1;transform:none}100%{opacity:0;transform:translate(var(--dx),var(--dy)) rotate(var(--rot)) scale(.45)}}'+
    '@media (prefers-reduced-motion:reduce){.breath .body,.fx span{animation:none!important}}';
  function R(a, b){ return a + Math.random()*(b - a); }
  function J(ms){ return ms * R(.82, 1.18); }
  function pick(w){ var t = 0, k; for (k in w) t += w[k]; var r = Math.random()*t; for (k in w) { r -= w[k]; if (r <= 0) return k; } return k; }

  class BuddyCat extends HTMLElement {
    static get observedAttributes(){ return ['mode','cue','scale','height','floor']; }
    constructor(){
      super();
      var r = this.attachShadow({mode:'open'});
      r.innerHTML = '<style>'+CSS+'</style><div class="floor"></div><div class="cat"><div class="body"><img alt=""></div></div>'+
        '<div class="fx"><span class="zzz">z z Z</span><span class="bang">!</span></div><div class="conf"></div>';
      this.$cat = r.querySelector('.cat'); this.$img = r.querySelector('img');
      this.$fx = r.querySelector('.fx'); this.$conf = r.querySelector('.conf'); this.$floor = r.querySelector('.floor');
      this.c = {x:40,y:0,dir:1,v:0,frame:'sit_side',energy:R(.7,1),shut:false,blinkAt:0,blinkUntil:0,again:false,jump:null,fx:'none'};
      this.q = []; this.cur = null; this.shown = null;
      this.addEventListener('click', e => this.onClick(e));
    }
    get _base(){ return this.getAttribute('base') || 'sprites/'; }
    get _scale(){ return parseFloat(this.getAttribute('scale')) || 2; }
    get _mode(){ return this.getAttribute('mode') || 'auto'; }
    connectedCallback(){
      ALL.concat(Object.keys(BLINK).map(n => n + '_blink')).forEach(n => { var i = new Image(); i.src = this._base + n + '.png'; });
      this.size();
      this.c.x = Math.max(4, (this.clientWidth || 300) * (parseFloat(this.getAttribute('start')) || 0.4) - this.cw()/2);
      this.c.dir = Math.random() < .5 ? 1 : -1;
      var m = this._mode;
      this.c.frame = m === 'sleep' ? 'ball' : m === 'front' ? 'sit_front' : m === 'tall' || m === 'alert' ? 'sit_tall' : m === 'groom' ? 'groom_0' : 'sit_side';
      if (m === 'sleep') this.c.energy = 0;
      this.q = []; this.think();
      this.paint();
      this.last = performance.now();
      this.raf = requestAnimationFrame(t => this.tick(t));
      this.ro = new ResizeObserver(() => this.clamp()); this.ro.observe(this);
    }
    disconnectedCallback(){ cancelAnimationFrame(this.raf); this.ro && this.ro.disconnect(); }
    attributeChangedCallback(n, o, v){
      if (!this.$cat || o === v) return;
      if (n === 'scale' || n === 'height' || n === 'floor') { this.size(); this.clamp(); }
      if (n === 'mode' && this.raf) this.interrupt(this.asleepNow() ? this.wakeSteps() : []);
      if (n === 'cue' && v && this.raf) this.cue(v.split(':')[0]);
      this.paint();
    }
    size(){
      var s = this._scale;
      this.style.height = (parseFloat(this.getAttribute('height')) || 150) + 'px';
      this.$cat.style.width = this.$fx.style.width = 64*s + 'px';
      this.$cat.style.height = 58*s + 'px';
      var h = parseFloat(this.getAttribute('height')) || 150;
      this.$fx.querySelectorAll('span').forEach(el => el.style.bottom = Math.min(46*s, h - 18 - 44) + 'px');
      this.$floor.style.display = this.getAttribute('floor') === 'none' ? 'none' : '';
    }
    cw(){ return 64*this._scale; }
    bounds(){ return {min:4, max:Math.max(8, this.clientWidth - this.cw() - 4)}; }
    clamp(){ var b = this.bounds(); this.c.x = Math.max(b.min, Math.min(b.max, this.c.x)); }
    asleepNow(){ var f = this.c.frame; return f === 'ball' || f === 'curl' || f === 'peek_b'; }

    // ---------- step builders ----------
    hold(f, ms, o){ return Object.assign({f:f, ms:J(ms)}, o || {}); }
    loop(frames, ms, reps){ var out = []; for (var r = 0; r < reps; r++) frames.forEach(f => out.push({f:f, ms:J(ms)})); return out; }
    move(to, gait){ return {move:to, gait:gait}; }
    call(fn){ return {call:fn}; }
    groomSteps(){
      var s = [this.hold('groom_0', 500)];
      var bouts = Math.random() < .4 ? 2 : 1;
      for (var b = 0; b < bouts; b++) {
        s = s.concat(this.loop(['groom_1','groom_2','groom_3','groom_4','groom_3','groom_2'], 170, Math.round(R(2, 4))));
        s.push(this.hold('groom_0', R(700, 1500)));
      }
      return s;
    }
    stretchSteps(){ return [this.hold('sit_side', 300), this.hold('stretch', 1100), this.hold('stretch', 300), this.hold('sit_side', 400)]; }
    jumpSteps(h){ var self = this; return [this.hold('jump_0', 280), this.call(() => self.arc(720, h || 1)), {f:'jump_1',ms:110},{f:'jump_2',ms:140},{f:'jump_3',ms:170},{f:'jump_4',ms:150},{f:'jump_5',ms:260}, this.hold('sit_side', 500)]; }
    celebrateSteps(){ var self = this; return [this.call(() => self.burst()), this.hold('jump_0', 160), this.call(() => self.arc(520, .9)), {f:'jump_2',ms:180},{f:'jump_3',ms:200}, this.hold('wave', 700), this.hold('sit_front', 260), this.hold('wave', 520), this.hold('sit_side', 600)]; }
    sleepSteps(){ return [this.hold('sit_droopy', 1100), this.hold('sit_droopy', 900), this.hold('loaf', 1200), this.hold('curl', 900), {f:'ball', ms:J(9000), fx:'sleep'}]; }
    wakeSteps(){ var self = this; return [this.hold('peek_b', 900), this.hold('curl', 380), this.hold('loaf', 600), this.hold('sit_droopy', 700), this.hold('sit_side', 350), this.hold('stretch', 1100), this.hold('sit_side', 500), this.call(() => { self.c.energy = R(.8, 1); })]; }
    goTo(x, gait){
      var c = this.c, b = this.bounds(), s = []; x = Math.max(b.min, Math.min(b.max, x));
      var dir = x > c.x ? 1 : -1;
      if (Math.abs(x - c.x) < 8) return s;
      if (dir !== c.dir) { s.push(this.hold(c.frame.indexOf('sit') === 0 ? c.frame : 'sit_side', 260)); s.push(this.call(() => { this.c.dir = dir; })); s.push(this.hold('walk_0', 160)); }
      s.push(this.move(x, gait));
      s.push(this.hold('walk_0', 240));
      return s;
    }

    // ---------- the brain ----------
    think(){
      var c = this.c, m = this._mode, b = this.bounds(), s = [];
      if (m === 'sleep') {
        if (!this.asleepNow()) s = this.sleepSteps();
        else s = Math.random() < .2 ? [this.hold('peek_b', 1400), {f:'ball', ms:J(8000), fx:'sleep'}] : [{f:'ball', ms:J(7000), fx:'sleep'}];
      }
      else if (m === 'auto') s = this.autoPlan();
      else if (m === 'walk') {
        var far = c.x - b.min < b.max - c.x ? b.max - R(0, 30) : b.min + R(0, 30);
        s = this.goTo(far, Math.random() < .3 ? 'stroll' : 'walk').concat([this.hold('sit_side', R(1200, 2600))]);
        if (Math.random() < .3) s = s.concat(this.groomSteps());
      }
      else if (m === 'wave') s = this.celebrateSteps().concat([this.hold(Math.random() < .5 ? 'sit_front' : 'sit_side', R(1800, 3200))]);
      else if (m === 'alert') {
        var a = pick({still:5, front:2, hop:1});
        s = a === 'still' ? [{f:'sit_tall', ms:J(2600), fx:'alert'}]
          : a === 'front' ? [{f:'sit_front', ms:J(1500), fx:'alert'}, {f:'sit_tall', ms:J(1500), fx:'alert'}]
          : [{f:'jump_0', ms:220, fx:'alert'}, {f:'sit_tall', ms:J(2000), fx:'alert'}];
      }
      else if (m === 'groom') s = this.groomSteps().concat(Math.random() < .25 ? [this.hold('sit_side', R(1500, 2500))] : []);
      else {
        var base = m === 'front' ? 'sit_front' : m === 'tall' ? 'sit_tall' : 'sit_side';
        var other = base === 'sit_front' ? 'sit_side' : 'sit_front';
        var p = pick({hold:6, look:2, groom:2, stretch:1});
        s = [this.hold(base, R(2600, 5200))];
        if (p === 'look') s.push(this.hold(other, R(1400, 2600)));
        if (p === 'groom') s = s.concat(this.groomSteps());
        if (p === 'stretch') s = s.concat(this.stretchSteps());
      }
      this.q = this.q.concat(s);
    }
    autoPlan(){
      var c = this.c, b = this.bounds(), w = b.max - b.min;
      if (this.asleepNow()) {
        if (Math.random() < .3) return this.wakeSteps();
        return Math.random() < .25 ? [this.hold('peek_b', 1200), {f:'ball', ms:J(7000), fx:'sleep'}] : [{f:'ball', ms:J(8000), fx:'sleep'}];
      }
      c.energy = Math.max(0, c.energy - R(.04, .09));
      if (c.energy < .1) return this.sleepSteps();
      var sleepy = c.energy < .35;
      var p = pick(sleepy ? {sit:3, droop:4, groom:2, stroll:1} : {wander:4, stroll:2, dash:1, sit:3, look:2, groom:2, stretch:1, hop:1});
      var sitAfter = () => this.hold(Math.random() < .3 ? 'sit_front' : 'sit_side', R(1400, 3200));
      if (p === 'wander') { var t = b.min + Math.random()*w; return this.goTo(t, Math.abs(t - c.x) > w*.55 && Math.random() < .5 ? 'run' : 'walk').concat([sitAfter()]); }
      if (p === 'stroll') return this.goTo(c.x + (Math.random() < .5 ? -1 : 1) * R(40, 110), 'stroll').concat([sitAfter()]);
      if (p === 'dash') { var e = c.dir > 0 ? b.max : b.min; if (Math.abs(e - c.x) < w*.3) e = c.dir > 0 ? b.min : b.max; return this.goTo(e, 'run').concat([this.hold('sit_tall', 900), sitAfter()]); }
      if (p === 'sit') return [this.hold('sit_side', R(2400, 4800))];
      if (p === 'look') return [this.hold('sit_side', 600), this.hold('sit_front', R(2000, 3800)), this.hold('sit_side', 500)];
      if (p === 'droop') return [this.hold('sit_droopy', R(2600, 4200)), this.hold('sit_side', R(800, 1400))];
      if (p === 'groom') return this.groomSteps();
      if (p === 'stretch') return this.stretchSteps();
      return this.jumpSteps();
    }
    interrupt(prefix){ this.cur = null; this.c.v = 0; this.q = prefix || []; if (!this.q.length) this.think(); this.next(); }
    cue(a){
      var pre = this.asleepNow() ? this.wakeSteps() : [];
      var s = a === 'celebrate' ? this.celebrateSteps().concat([this.hold('sit_front', 1400)], this.celebrateSteps(), [this.hold('sit_front', 2200)]) : a === 'jump' ? this.jumpSteps(.7) : a === 'stretch' ? this.stretchSteps()
        : a === 'alert' ? [{f:'sit_tall', ms:1600, fx:'alert'}, this.hold('sit_side', 400)] : [];
      this.interrupt(pre.concat(s));
    }
    arc(ms, h){ this.c.jump = {t0:performance.now(), ms:ms, h:h}; }
    burst(){
      var el = this.$conf; el.innerHTML = '';
      var cols = ['var(--color-accent)','var(--color-accent-300)','var(--color-accent-700)','var(--color-neutral-700)'];
      var cx = this.c.x + this.cw()/2;
      for (var i = 0; i < 16; i++) {
        var s = document.createElement('i'), a = Math.PI*2*i/16 + Math.random()*.35, d = 45 + Math.random()*50;
        s.style.left = cx + 'px'; s.style.bottom = (18 + 28*this._scale) + 'px';
        s.style.setProperty('--dx', Math.cos(a)*d + 'px'); s.style.setProperty('--dy', (Math.sin(a)*d - 26) + 'px');
        s.style.setProperty('--rot', Math.random()*380 + 'deg'); s.style.background = cols[i % 4];
        s.style.animationDelay = Math.random()*.06 + 's'; el.appendChild(s);
      }
    }
    onClick(e){
      var c = this.c, rect = this.getBoundingClientRect(), x = e.clientX - rect.left;
      if (this.asleepNow()) { this.interrupt(this.wakeSteps()); return; }
      var onCat = x > c.x - 10 && x < c.x + this.cw() + 10;
      if (onCat) { c.energy = Math.min(1, c.energy + .35); this.interrupt([{f:'sit_tall', ms:1300, fx:'alert'}, this.hold('sit_front', 1600)]); }
      else if (this._mode === 'auto' || this._mode === 'walk') this.interrupt(this.goTo(x - this.cw()/2, Math.abs(x - c.x) > 160 ? 'run' : 'walk').concat([this.hold('sit_front', 1800)]));
    }

    // ---------- runtime ----------
    next(){
      while (true) {
        if (!this.q.length) this.think();
        var s = this.q.shift();
        if (s.call) { s.call(); continue; }
        this.cur = Object.assign({acc:0}, s);
        if (s.f) this.c.frame = s.f;
        this.c.fx = s.fx || 'none';
        if (s.move != null) { this.gait = GAIT[s.gait || 'walk']; this.gi = 0; this.dist = 0; this.c.frame = this.gait.frames[0]; }
        return;
      }
    }
    pxs(g){ return 45*this._scale*g.stride / (g.frames.length*.15) * g.vmax / (g === GAIT.run ? g.vmax/1.9 : 1) ; }
    tick(now){
      var c = this.c, dt = Math.min(64, now - this.last); this.last = now;
      if (!this.cur) this.next();
      var s = this.cur;
      if (s.move != null) {
        var g = this.gait, d = s.move - c.x, ad = Math.abs(d);
        c.dir = d >= 0 ? 1 : -1;
        if (g === GAIT.run && ad < 70) { g = this.gait = GAIT.walk; this.gi = 0; }
        var vmax = this.pxs(g), vT = Math.min(vmax, 18 + ad*2.4);
        var acc = vmax * 2.6 * dt/1000;
        c.v += Math.max(-acc*1.6, Math.min(acc, vT - c.v));
        var step = Math.min(ad, c.v*dt/1000);
        c.x += c.dir*step;
        this.dist += step;
        var stridePx = 45*this._scale*g.stride / g.frames.length;
        while (this.dist >= stridePx) { this.dist -= stridePx; this.gi = (this.gi + 1) % g.frames.length; }
        c.frame = g.frames[this.gi];
        if (ad - step < 1.5) { c.v = 0; this.cur = null; }
      } else {
        s.acc += dt;
        if (s.acc >= s.ms) this.cur = null;
      }
      if (c.jump) { var p = (now - c.jump.t0)/c.jump.ms; if (p >= 1) { c.jump = null; c.y = 0; } else c.y = Math.sin(Math.PI*p) * 30 * c.jump.h * this._scale/2.2; }
      var still = !(s && s.move != null) && !c.jump && BLINK[c.frame];
      if (still) {
        var sleepy = c.energy < .35 || c.frame === 'sit_droopy';
        if (c.shut) { if (now >= c.blinkUntil) { c.shut = false; if (c.again) { c.again = false; c.blinkAt = now + 140; } else c.blinkAt = now + (sleepy ? R(900, 2300) : R(2200, 5600)); } }
        else if (now >= c.blinkAt) { c.shut = true; c.blinkUntil = now + (sleepy ? R(280, 520) : R(90, 140)); if (!sleepy && Math.random() < .25) c.again = true; }
      } else if (c.shut) { c.shut = false; c.blinkAt = now + 1000; }
      this.paint();
      this.raf = requestAnimationFrame(t => this.tick(t));
    }
    paint(){
      var c = this.c, want = c.shut && BLINK[c.frame] ? c.frame + '_blink' : c.frame;
      if (want !== this.shown) { this.shown = want; this.$img.src = this._base + want + '.png'; }
      this.$cat.style.transform = this.$fx.style.transform = 'translate3d(' + c.x.toFixed(1) + 'px,' + (-(c.y||0)).toFixed(1) + 'px,0)';
      this.$cat.classList.toggle('flip', c.dir === -1);
      this.$cat.classList.toggle('breath', c.frame === 'ball');
      if (this.$fx.dataset.fx !== c.fx) this.$fx.dataset.fx = c.fx;
    }
  }
  customElements.define('buddy-cat', BuddyCat);
})();
