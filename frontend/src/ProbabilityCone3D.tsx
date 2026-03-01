import { useMemo, useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import * as THREE from 'three';
import type { ConeRenderData } from './types';

interface ProbabilityCone3DProps {
  data: ConeRenderData | null;
  horizonDays: number;
  highlightRange?: [number, number];
  targetLine?: number;
  liquidationPrice?: number;
  takeProfit?: number;
  stopLoss?: number;
}

function getLogNormalDensity(x: number, currentPrice: number, volatility: number, tYears: number): number {
  if (x <= 0) return 0;
  if (tYears === 0) return x === currentPrice ? 1 : 0;
  const mu = Math.log(currentPrice) - 0.5 * volatility * volatility * tYears;
  const sigma = volatility * Math.sqrt(tYears);
  const coeff = 1 / (x * sigma * Math.sqrt(2 * Math.PI));
  const exponent = -Math.pow(Math.log(x) - mu, 2) / (2 * sigma * sigma);
  return coeff * Math.exp(exponent);
}

const Surface = ({ data, horizonDays, highlightRange, targetLine, liquidationPrice, takeProfit, stopLoss }: ProbabilityCone3DProps) => {
  const meshRef = useRef<THREE.Mesh>(null);
  const materialRef = useRef<THREE.ShaderMaterial>(null);

  const { geometry, uniforms } = useMemo(() => {
    if (!data) {
      return {
        geometry: new THREE.PlaneGeometry(1, 1),
        uniforms: {
          uTime: { value: 0 },
          uColorStart: { value: new THREE.Color('#1e293b') },
          uColorEnd: { value: new THREE.Color('#38bdf8') },
          uHighlightMin: { value: -1 },
          uHighlightMax: { value: -1 },
          uHighlightColor: { value: new THREE.Color('#ffffff') },
          uTargetLine: { value: -1 },
          uLiquidation: { value: -1 },
          uTakeProfit: { value: -1 },
          uStopLoss: { value: -1 },
        },
      };
    }

    const stepsX = 80;
    const stepsZ = 160;

    const geom = new THREE.PlaneGeometry(16, 16, stepsX - 1, stepsZ - 1);
    const positions = geom.attributes.position.array;

    const minPrice = data.minPrice;
    const maxPrice = data.maxPrice;
    const priceRange = maxPrice - minPrice;

    const refI = Math.max(1, Math.floor(stepsX * 0.15));
    const tYearsRef = (refI / (stepsX - 1)) * (horizonDays / 365);
    const refDensity = getLogNormalDensity(data.currentPrice, data.currentPrice, data.volatility, tYearsRef);

    for (let i = 0; i < stepsX; i++) {
      const tYears = (i / (stepsX - 1)) * (horizonDays / 365);
      for (let j = 0; j < stepsZ; j++) {
        const idx = (j * stepsX + i) * 3;
        const price = minPrice + (j / (stepsZ - 1)) * priceRange;

        let density = 0;
        if (i > 0) {
          density = getLogNormalDensity(price, data.currentPrice, data.volatility, tYears);
        } else {
          if (Math.abs(price - data.currentPrice) < priceRange * 0.01) {
            density = refDensity * 2.0;
          }
        }

        const normalized = Math.min(density / refDensity, 2.5);
        const z = Math.pow(normalized, 0.7) * 3.0;
        positions[idx + 2] = z;
      }
    }

    geom.computeVertexNormals();

    const unifs = {
      uTime: { value: 0 },
      uColorStart: { value: new THREE.Color('#1e293b') },
      uColorEnd: { value: new THREE.Color('#38bdf8') },
      uHighlightMin: { value: highlightRange ? (highlightRange[0] - minPrice) / priceRange : -1 },
      uHighlightMax: { value: highlightRange ? (highlightRange[1] - minPrice) / priceRange : -1 },
      uHighlightColor: { value: new THREE.Color('#ffffff') },
      uTargetLine: { value: targetLine != null ? (targetLine - minPrice) / priceRange : -1 },
      uLiquidation: { value: liquidationPrice != null ? (liquidationPrice - minPrice) / priceRange : -1 },
      uTakeProfit: { value: takeProfit != null ? (takeProfit - minPrice) / priceRange : -1 },
      uStopLoss: { value: stopLoss != null ? (stopLoss - minPrice) / priceRange : -1 },
    };

    return { geometry: geom, uniforms: unifs };
  }, [data, horizonDays, highlightRange, targetLine, liquidationPrice, takeProfit, stopLoss]);

  useFrame((state) => {
    if (materialRef.current) {
      materialRef.current.uniforms.uTime.value = state.clock.elapsedTime;
    }
  });

  if (!data) return null;

  return (
    <mesh
      ref={meshRef}
      geometry={geometry}
      rotation={[-Math.PI / 2, 0, 0]}
      position={[0, -2, 0]}
    >
      <shaderMaterial
        ref={materialRef}
        uniforms={uniforms}
        vertexShader={`
          varying vec2 vUv;
          varying float vElevation;
          void main() {
            vUv = uv;
            vElevation = position.z;
            vec4 modelPosition = modelMatrix * vec4(position, 1.0);
            vec4 viewPosition = viewMatrix * modelPosition;
            vec4 projectedPosition = projectionMatrix * viewPosition;
            gl_Position = projectedPosition;
          }
        `}
        fragmentShader={`
          uniform vec3 uColorStart;
          uniform vec3 uColorEnd;
          uniform float uHighlightMin;
          uniform float uHighlightMax;
          uniform vec3 uHighlightColor;
          uniform float uTargetLine;
          uniform float uLiquidation;
          uniform float uTakeProfit;
          uniform float uStopLoss;
          uniform float uTime;

          varying vec2 vUv;
          varying float vElevation;

          void main() {
            float mixStrength = smoothstep(0.0, 3.0, vElevation);
            vec3 color = mix(uColorStart, uColorEnd, mixStrength);

            float gridX = mod(vUv.x * 80.0, 1.0);
            float gridY = mod(vUv.y * 160.0, 1.0);

            if (gridX < 0.05 || gridY < 0.05) {
              color += vec3(0.1, 0.3, 0.6) * (1.0 - mixStrength * 0.5);
            }

            if (uHighlightMin >= 0.0 && uHighlightMax >= 0.0) {
              if (vUv.y >= uHighlightMin && vUv.y <= uHighlightMax) {
                float pulse = 0.5 + 0.5 * sin(uTime * 2.0 - vUv.x * 5.0);
                color = mix(color, uHighlightColor, 0.2 + 0.15 * pulse);
              }
            }

            if (uTargetLine >= 0.0 && abs(vUv.y - uTargetLine) < 0.003) {
              color = vec3(1.0, 1.0, 1.0);
              color += vec3(0.5, 0.5, 0.5) * (0.5 + 0.5 * sin(uTime * 3.0));
            }

            if (uLiquidation >= 0.0 && abs(vUv.y - uLiquidation) < 0.003) {
              color = vec3(1.0, 0.1, 0.1);
              color += vec3(0.8, 0.0, 0.0) * (0.5 + 0.5 * sin(uTime * 4.0));
            }

            if (uTakeProfit >= 0.0 && abs(vUv.y - uTakeProfit) < 0.002) {
              color = vec3(0.1, 1.0, 0.3);
            }

            if (uStopLoss >= 0.0 && abs(vUv.y - uStopLoss) < 0.002) {
              color = vec3(1.0, 0.5, 0.0);
            }

            float alpha = smoothstep(0.0, 0.05, vUv.x) * smoothstep(1.0, 0.8, vUv.x);
            alpha *= smoothstep(0.0, 0.1, vUv.y) * smoothstep(1.0, 0.9, vUv.y);
            alpha *= 0.6 + 0.4 * mixStrength;

            gl_FragColor = vec4(color, alpha);
          }
        `}
        transparent={true}
        side={THREE.DoubleSide}
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </mesh>
  );
};

export default function ProbabilityCone3D(props: ProbabilityCone3DProps) {
  return (
    <div className="absolute inset-0 w-full h-full bg-[#000000] z-0">
      <Canvas camera={{ position: [12, 6, 12], fov: 40 }}>
        <color attach="background" args={['#000000']} />
        <ambientLight intensity={0.2} />
        <pointLight position={[10, 10, 10]} intensity={0.5} />

        <Surface {...props} />

        <OrbitControls
          enableZoom={true}
          enablePan={false}
          minPolarAngle={Math.PI / 8}
          maxPolarAngle={Math.PI / 2.1}
          autoRotate={true}
          autoRotateSpeed={0.3}
          enableDamping={true}
          dampingFactor={0.05}
        />
      </Canvas>
    </div>
  );
}
