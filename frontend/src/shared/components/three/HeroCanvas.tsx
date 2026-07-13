import { Canvas } from '@react-three/fiber'
import { Float, MeshDistortMaterial, Sparkles } from '@react-three/drei'

/**
 * Lightweight three.js hero centerpiece (R3F + drei). A single distorted
 * icosahedron floating with sparkle particles — low-poly, capped DPR, all
 * solid colors (no gradient materials). Lazy-loaded via GuardedHero3D so it
 * never enters the main bundle.
 */
function Scene() {
  return (
    <>
      <ambientLight intensity={0.5} />
      <directionalLight position={[5, 5, 5]} intensity={1} />
      <Float speed={2} rotationIntensity={1.2} floatIntensity={1.5}>
        <mesh>
          <icosahedronGeometry args={[1.2, 4]} />
          <MeshDistortMaterial
            color="#2563eb"
            emissive="#1d4ed8"
            roughness={0.2}
            metalness={0.4}
            distort={0.35}
            speed={2}
          />
        </mesh>
      </Float>
      <Sparkles count={40} scale={6} size={2} color="#facc15" opacity={0.6} />
    </>
  )
}

export default function HeroCanvas() {
  return (
    <Canvas
      dpr={[1, 1.5]}
      camera={{ position: [0, 0, 5], fov: 45 }}
      gl={{ antialias: true, alpha: true }}
      className="h-full w-full"
    >
      <Scene />
    </Canvas>
  )
}
