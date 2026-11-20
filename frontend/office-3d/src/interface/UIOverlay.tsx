
import React, { useState } from 'react';
import { getAgentSet, getAllAgents, getAllCharacters } from '../data/agents';
import { useUiStore } from '../integration/store/uiStore';
import InfoModal from './InfoModal';

import { MessageSquareWarning, PartyPopper, Siren, Loader2 } from 'lucide-react';
import { Task, useCoreStore } from '../integration/store/coreStore';
import { useTeamStore, useActiveTeam } from '../integration/store/teamStore';
import { USER_COLOR, USER_COLOR_LIGHT, USER_COLOR_SOFT } from '../theme/brand';



interface AlertBubbleProps {
  icon: React.ReactNode;
  position: { x: number; y: number };
  visible: boolean;
  color?: string;
  onClick?: () => void;
}

const AlertBubble: React.FC<AlertBubbleProps> = ({ icon, position, visible, color = '#facc15', onClick }) => {
  if (!visible) return null;

  return (
    <div
      className={`absolute z-20 ${onClick ? 'pointer-events-auto cursor-pointer' : 'pointer-events-none'}`}
      style={{
        left: position.x,
        top: position.y,
        transform: 'translate(-50%, -100%) translateY(-10px)'
      }}
      onClick={(e) => {
        if (onClick) {
          e.stopPropagation();
          onClick();
        }
      }}
    >
      <div
        className={`bg-darkDelegation/90 backdrop-blur-md p-1.5 rounded-full border border-white/10 shadow-xl flex items-center justify-center hover:scale-110 active:scale-95 transition-transform ${onClick ? 'hover:border-white/30' : ''}`}
        style={{ color }}
      >
        {icon}
      </div>
    </div>
  );
};

type PhaseLabel = { text: string; className: string };

function getAgentPhaseLabel(
  agentIndex: number,
  leadAgentIndex: number,
  tasks: Task[],
  phase: string,
  isGeneratingAsset: boolean,
  fallback: string,
): PhaseLabel {
  if (isGeneratingAsset && agentIndex === leadAgentIndex) {
    return { text: 'Delivering...', className: 'text-indigo-400 animate-pulse' };
  }
  if (agentIndex === leadAgentIndex && phase === 'done') {
    return { text: 'Project Ready!', className: 'text-yellow-400' };
  }
  const holdTask = tasks.find(
    t => t.assignedAgentId === agentIndex && t.status === 'on_hold',
  );
  if (holdTask && phase !== 'done') {
    return { text: 'Approval Needed', className: 'text-[#7EACEA]' };
  }
  const activeTask = tasks.find(
    t => t.assignedAgentId === agentIndex && t.status === 'in_progress',
  );
  if (activeTask) {
    return { text: 'Working', className: 'text-emerald-400' };
  }
  return { text: fallback, className: 'text-white/70' };
}

const UIOverlay: React.FC = () => {
  const {
    selectedNpcIndex,
    selectedPosition,
    hoveredNpcIndex,
    hoveredPoiLabel,
    hoverPosition,
    npcScreenPositions,
    setSelectedNpc,
    liveTelemetry,
  } = useUiStore();
  const [isHelpOpen, setHelpOpen] = useState(false);
  const {
    tasks,
    phase,
    isGeneratingAsset,
  } = useCoreStore();
  const system = useActiveTeam();
  const npcAgents = getAllAgents(system);
  const allPossibleAgents = getAllCharacters(system);

  const selectedAgent = selectedNpcIndex != null ? allPossibleAgents.find(a => a.index === selectedNpcIndex) as any ?? null : null;
  const hoveredAgent = hoveredNpcIndex != null ? allPossibleAgents.find(a => a.index === hoveredNpcIndex) as any ?? null : null;


  return (
    <div className="absolute inset-0 pointer-events-none z-10 overflow-hidden select-none">
      {/* 1. Live Telemetry & Agent Floating Status Bubbles */}
      {npcAgents.map((agent) => {
        const pos = npcScreenPositions[agent.index];
        if (!pos) return null;

        const isCurrentlyHovered = hoveredNpcIndex === agent.index || selectedNpcIndex === agent.index;
        if (isCurrentlyHovered) return null;

        const telemetry = liveTelemetry?.[agent.index];
        const isLiveActive = telemetry && (telemetry.status === 'working' || telemetry.status === 'delegating');

        if (isLiveActive) {
          const statusLabel = telemetry.status === 'delegating' ? 'YÖNLENDİRİYOR' : 'ÇALIŞIYOR';
          const statusColor = telemetry.status === 'delegating' ? 'text-amber-300' : 'text-emerald-400';
          return (
            <div
              key={`telemetry-${agent.index}`}
              className="absolute z-25 pointer-events-auto cursor-pointer transition-all duration-75 ease-out"
              style={{
                left: pos.x,
                top: pos.y,
                transform: 'translate(-50%, -100%) translateY(-12px)',
              }}
              onClick={(e) => {
                e.stopPropagation();
                setSelectedNpc(agent.index);
              }}
            >
              <div className="bg-darkDelegation/95 backdrop-blur-md px-3 py-1.5 rounded-2xl border border-white/20 shadow-2xl flex flex-col items-center gap-0.5 max-w-[240px]">
                <div className="flex items-center gap-1.5 whitespace-nowrap">
                  <Loader2 size={12} className="animate-spin text-emerald-400 shrink-0" />
                  <div className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: agent.color }} />
                  <span className="text-[10px] font-black uppercase tracking-wider text-white">{agent.name}</span>
                  <span className="text-[10px] text-white/40">·</span>
                  <span className={`text-[9px] font-extrabold uppercase tracking-wider ${statusColor}`}>{statusLabel}</span>
                </div>
                {telemetry.task && (
                  <div className="text-[10px] text-white/85 font-medium truncate max-w-[220px]">
                    {telemetry.task}
                  </div>
                )}
              </div>
            </div>
          );
        }

        // Default compact name & status bubble above each of the 8 agents
        const isRecentDone = telemetry && telemetry.status === 'done' && (Date.now() - telemetry.updatedAt < 15000);
        return (
          <div
            key={`nameplate-${agent.index}`}
            className="absolute z-20 pointer-events-auto cursor-pointer transition-all duration-75 ease-out"
            style={{
              left: pos.x,
              top: pos.y,
              transform: 'translate(-50%, -100%) translateY(-10px)',
            }}
            onClick={(e) => {
              e.stopPropagation();
              setSelectedNpc(agent.index);
            }}
          >
            <div className="bg-darkDelegation/85 backdrop-blur-md px-2.5 py-1 rounded-full border border-white/10 shadow-lg flex items-center gap-1.5 whitespace-nowrap hover:scale-105 transition-transform">
              <div className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: agent.color }} />
              <span className="text-[10px] font-bold tracking-wider text-white">{agent.name}</span>
              {isRecentDone && (
                <span className="text-[9px] font-extrabold uppercase text-emerald-400 ml-1">✓</span>
              )}
            </div>
          </div>
        );
      })}

      {/* 2. Selection/Hover/Project Ready Bubble (Detailed) */}
      {(() => {
        // Priority 1: Selected Agent
        if (selectedAgent && selectedPosition) {
          const isLeadAgentProjectReady = selectedAgent.index === system.leadAgent.index && phase === 'done';
          const label = getAgentPhaseLabel(selectedAgent.index, system.leadAgent.index, tasks, phase, isGeneratingAsset, '');

          return (
            <div
              className="absolute z-25 pointer-events-none transition-all duration-75 ease-out"
              style={{
                left: selectedPosition.x,
                top: selectedPosition.y,
                transform: 'translate(-50%, -100%) translateY(-10px)'
              }}
            >
              <div className="bg-darkDelegation/90 backdrop-blur-md px-3 py-1.5 rounded-full border border-white/10 shadow-xl flex items-center gap-2 whitespace-nowrap animate-in fade-in zoom-in-95 duration-200">
                <div
                  className="w-2 h-2 rounded-full shrink-0"
                  style={{ backgroundColor: selectedAgent.color }}
                />
                <div className="flex items-center gap-1.5">
                  {selectedAgent.index === system.user.index ? (

                    <span className="text-[10px] font-black uppercase tracking-widest text-white">{selectedAgent.name} (You)</span>
                  ) : isLeadAgentProjectReady ? (
                    <span className={`text-[10px] font-black uppercase tracking-widest ${label.className}`}>
                      {label.text}
                    </span>
                  ) : (
                    <>
                      <span className="text-[10px] font-black uppercase tracking-widest text-white">
                        {selectedAgent.name}
                      </span>
                      {label.text && (
                        <>
                          <span className="text-[10px] font-medium uppercase tracking-widest text-white/40">·</span>
                          <span className={`text-[10px] font-bold uppercase tracking-widest ${label.className}`}>
                            {label.text}
                          </span>
                        </>
                      )}
                    </>
                  )}
                </div>
              </div>
            </div>
          );
        }

        // Priority 2: Hovered Agent with dynamic phase label (only if not selected)
        if (hoveredAgent && hoverPosition && hoveredNpcIndex !== selectedNpcIndex) {
          const isLeadAgentProjectReady = hoveredAgent.index === system.leadAgent.index && phase === 'done';
          const label = getAgentPhaseLabel(hoveredAgent.index, system.leadAgent.index, tasks, phase, isGeneratingAsset, '');

          return (
            <div
              className="absolute z-25 pointer-events-none transition-all duration-75 ease-out"
              style={{
                left: hoverPosition.x,
                top: hoverPosition.y,
                transform: 'translate(-50%, -100%) translateY(-10px)'
              }}
            >
              <div className="bg-darkDelegation/90 backdrop-blur-md px-3 py-1.5 rounded-full border border-white/10 shadow-xl flex items-center gap-2 whitespace-nowrap animate-in fade-in zoom-in-95 duration-200">
                <div
                  className="w-2 h-2 rounded-full shrink-0"
                  style={{ backgroundColor: hoveredAgent.color }}
                />
                <div className="flex items-center gap-1.5">
                  {hoveredAgent.index === system.user.index ? (

                    <span className="text-[10px] font-black uppercase tracking-widest text-white">{hoveredAgent.name} (You)</span>
                  ) : isLeadAgentProjectReady ? (
                    <span className={`text-[10px] font-black uppercase tracking-widest ${label.className}`}>
                      {label.text}
                    </span>
                  ) : (
                    <>
                      <span className="text-[10px] font-black uppercase tracking-widest text-white">
                        {hoveredAgent.name}
                      </span>
                      {label.text && (
                        <>
                          <span className="text-[10px] font-medium uppercase tracking-widest text-white/40">·</span>
                          <span className={`text-[10px] font-bold uppercase tracking-widest ${label.className}`}>
                            {label.text}
                          </span>
                        </>
                      )}
                    </>
                  )}
                </div>
              </div>
            </div>
          );
        }

        return null;
      })()}

      {/* POI Hover Bubble */}
      {hoveredPoiLabel && hoverPosition && (
        <div
          className="absolute z-10 pointer-events-none transition-all duration-75 ease-out"
          style={{
            left: hoverPosition.x,
            top: hoverPosition.y,
            transform: 'translate(-50%, -100%) translateY(-10px)'
          }}
        >
          <div className="bg-darkDelegation/90 backdrop-blur-md px-3 py-1.5 rounded-full border border-white/10 shadow-xl flex items-center gap-2 whitespace-nowrap animate-in fade-in zoom-in-95 duration-200">
            <span className="text-[10px] font-black uppercase tracking-widest text-white">{hoveredPoiLabel}</span>
          </div>
        </div>
      )}

      {/* Help Modal */}
      {isHelpOpen && <InfoModal onClose={() => setHelpOpen(false)} />}
    </div>
  );
};

export default UIOverlay;
