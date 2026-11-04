import * as THREE from 'three';
import { TaserState } from './TaserState.mjs';
/** Call update(deltaSeconds) each frame. Do not also run the included clips on these joints. */
export class TaserVRController {
  constructor(gltf, options = {}) {
    this.root = gltf.scene.getObjectByName('TaserVR');
    if (!this.root) throw new Error('TaserVR root missing');
    const get = name => { const o = this.root.getObjectByName(name); if (!o) throw new Error(`Missing ${name}`); return o; };
    this.trigger = get('TriggerPivot'); this.selector = get('SelectorPivot'); this.module = get('ModulePivot');
    this.triggerEnd = get('TriggerPressedPose'); this.selectorEnd = get('SelectorOnPose'); this.moduleEnd = get('ModuleOutPose');
    this.triggerRest = this.trigger.quaternion.clone(); this.selectorRest = this.selector.quaternion.clone(); this.moduleRest = this.module.position.clone();
    this.fireOrigin = get('FireOrigin'); this.fireForward = get('FireForward');
    this.selectorAmount = 0;
    this.state = new TaserState({ ...options, onUse: event => options.onUse?.({ ...event, ...this.getUseRay() }) });
    this.update(0);
  }
  getUseRay() {
    this.root.updateWorldMatrix(true,true);
    const origin = this.fireOrigin.getWorldPosition(new THREE.Vector3());
    const direction = this.fireForward.getWorldPosition(new THREE.Vector3()).sub(origin).normalize();
    return { origin, direction };
  }
  grab(handObject, handedness = 'right') {
    const grip = this.root.getObjectByName(handedness === 'left' ? 'Grip_L' : 'Grip_R');
    this.root.updateWorldMatrix(true,true);
    const gripInRoot = new THREE.Matrix4().copy(this.root.matrixWorld).invert().multiply(grip.matrixWorld);
    handObject.add(this.root);
    gripInRoot.invert().decompose(this.root.position,this.root.quaternion,this.root.scale);
    this.state.setHeld(true);
  }
  release(worldParent) {
    if (!worldParent?.isObject3D) throw new Error('Pass the scene/physics parent on release');
    worldParent.attach(this.root); this.state.setHeld(false); this.update(0);
  }
  setTrigger(value) { return this.state.setTrigger(value); }
  setArmed(value) { return this.state.setArmed(value); }
  reload() { return this.state.reload(); }
  removeModule() { return this.state.removeModule(); }
  insertModule(charges) { return this.state.insertModule(charges); }
  update(dt) {
    this.state.update(dt);
    this.trigger.quaternion.copy(this.triggerRest).slerp(this.triggerEnd.quaternion,this.state.trigger);
    this.selectorAmount = THREE.MathUtils.damp(this.selectorAmount,this.state.armed?1:0,20,dt);
    this.selector.quaternion.copy(this.selectorRest).slerp(this.selectorEnd.quaternion,this.selectorAmount);
    this.module.position.copy(this.moduleRest).lerp(this.moduleEnd.position,this.state.moduleAmount);
  }
  /** Feed these boxes to your own physics engine. Matrix includes world scale. */
  getColliderBoxes() {
    this.root.updateWorldMatrix(true,true); const boxes=[];
    this.root.traverse(o => { if (o.name.startsWith('COL_') && (o.name!=='COL_Module' || this.state.moduleSeated)) boxes.push({ name:o.name, unitSize:[1,1,1], matrixWorld:o.matrixWorld.clone() }); });
    return boxes;
  }
}
