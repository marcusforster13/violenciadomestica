/** Engine-independent GAME state. No hardware behavior is represented. */
export class TaserState {
  constructor({ capacity = 10, cooldown = 0.35, reloadDuration = 1.1, onUse = () => {}, onChange = () => {} } = {}) {
    if (!Number.isInteger(capacity) || capacity < 1 || !Number.isFinite(cooldown) || cooldown < 0 || !Number.isFinite(reloadDuration) || reloadDuration <= 0) throw new RangeError('Invalid gameplay settings');
    this.capacity = capacity; this.cooldownDuration = cooldown; this.reloadDuration = reloadDuration;
    this.onUse = onUse; this.onChange = onChange;
    this.held = false; this.armed = false; this.trigger = 0; this.latched = false;
    this.moduleSeated = true; this.moduleAmount = 0; this.charges = capacity;
    this.cooldown = 0; this.reloading = false; this.reloadElapsed = 0;
  }
  snapshot() { return { held:this.held, armed:this.armed, trigger:this.trigger, moduleSeated:this.moduleSeated, moduleAmount:this.moduleAmount, charges:this.charges, cooldown:this.cooldown, reloading:this.reloading }; }
  changed() { this.onChange(this.snapshot()); }
  setHeld(value) {
    this.held = !!value;
    if (!this.held) {
      this.armed = false; this.trigger = 0; this.latched = false;
      if (this.reloading) { this.reloading = false; this.moduleSeated = false; this.moduleAmount = 1; this.charges = 0; }
    }
    this.changed();
  }
  setArmed(value) {
    if (value && (!this.held || this.reloading || !this.moduleSeated || this.trigger > .2)) return false;
    this.armed = !!value; this.changed(); return true;
  }
  setTrigger(value) {
    if (!Number.isFinite(value)) throw new RangeError('Trigger must be finite');
    this.trigger = this.held ? Math.max(0, Math.min(1, value)) : 0;
    if (this.trigger <= .2) this.latched = false;
    let used = false;
    if (this.trigger >= .8 && !this.latched) {
      this.latched = true;
      if (this.held && this.armed && this.moduleSeated && !this.reloading && this.charges > 0 && this.cooldown <= 0) {
        --this.charges; this.cooldown = this.cooldownDuration; used = true;
        this.onUse({ remaining: this.charges });
      }
    }
    this.changed(); return used;
  }
  removeModule() {
    if (!this.held || this.armed || this.trigger > .2 || this.reloading || !this.moduleSeated) return false;
    this.moduleSeated = false; this.moduleAmount = 1; this.charges = 0; this.changed(); return true;
  }
  insertModule(charges = this.capacity) {
    if (!Number.isInteger(charges) || charges < 0 || charges > this.capacity) throw new RangeError('Invalid charges');
    if (!this.held || this.armed || this.trigger > .2 || this.reloading || this.moduleSeated) return false;
    this.moduleSeated = true; this.moduleAmount = 0; this.charges = charges; this.changed(); return true;
  }
  reload() {
    if (!this.held || this.reloading || this.trigger > .2) return false;
    this.armed = false; this.reloading = true; this.reloadElapsed = 0;
    this.reloadStartAmount = this.moduleAmount; this.moduleSeated = false; this.charges = 0; this.changed(); return true;
  }
  update(dt) {
    if (!Number.isFinite(dt) || dt < 0) throw new RangeError('dt must be finite and nonnegative');
    this.cooldown = Math.max(0, this.cooldown - dt);
    if (!this.reloading) return;
    this.reloadElapsed += dt;
    const t = this.reloadElapsed / this.reloadDuration;
    const ease = x => { x = Math.max(0, Math.min(1, x)); return x*x*(3-2*x); };
    this.moduleAmount = t < .3 ? this.reloadStartAmount + (1-this.reloadStartAmount)*ease(t/.3) : t < .6 ? 1 : 1-ease((t-.6)/.4);
    if (t >= 1) { this.reloading = false; this.moduleSeated = true; this.moduleAmount = 0; this.charges = this.capacity; }
    this.changed();
  }
}
