import React, { useMemo, useRef, useState, useEffect } from 'react';
import { ChevronDown, Send } from 'lucide-react';
import { Streamdown } from 'streamdown';

interface SponsoredUnit {
  ad_id: string;
  title: string;
  description: string;
  landing_url: string;
  category: string;
  brand: string;
  disclosure: string;
  why_shown: string;
  coupon_code?: string;
  metadata?: Record<string, any>;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sponsored_unit?: SponsoredUnit;
  intent_label?: string;
  timestamp: Date;
}

export default function CAIPDemo() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [placementMode, setPlacementMode] = useState<'subtle' | 'direct' | 'interactive'>('subtle');
  const [expandedWhy, setExpandedWhy] = useState<string | null>(null);
  const [hiddenAds, setHiddenAds] = useState<Set<string>>(new Set());
  const [showSponsored, setShowSponsored] = useState(true);
  const [activeAskAdId, setActiveAskAdId] = useState<string | null>(null);
  const [askInput, setAskInput] = useState('');
  const [askLoading, setAskLoading] = useState(false);
  const [askResponses, setAskResponses] = useState<Record<string, string>>({});
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const sessionId = useRef(Math.random().toString(36).substring(7));
  const impressionLogged = useRef<Set<string>>(new Set());
  const partnerKey = useMemo(() => 'demo_key', []);
  const userId = useMemo(() => 'demo_user', []);

  const formatTime = (timestamp: Date) =>
    timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  const getUtilityBullets = (unit: SponsoredUnit) => {
    const bullets: string[] = [];
    const features = unit.metadata?.features || unit.metadata?.bullets;

    if (Array.isArray(features)) {
      bullets.push(...features.filter(Boolean).slice(0, 4));
    }

    if (bullets.length < 2 && unit.description) {
      const sentences = unit.description
        .split(/(?<=[.!?])\s+/)
        .map((sentence) => sentence.trim())
        .filter(Boolean);
      bullets.push(...sentences.slice(0, 4 - bullets.length));
    }

    if (bullets.length < 2 && unit.category) {
      bullets.push(`Category: ${unit.category}`);
    }

    if (bullets.length < 2 && unit.brand) {
      bullets.push(`Provider: ${unit.brand}`);
    }

    if (bullets.length < 2) {
      bullets.push('Explore compatibility and fit');
    }

    return bullets.slice(0, 4);
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const logEvent = async (payload: Record<string, any>) => {
    try {
      await fetch('/v1/events', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          partner_key: partnerKey,
          session_id: sessionId.current,
          ...payload,
        }),
      });
    } catch (error) {
      console.warn('Event logging failed', error);
    }
  };

  useEffect(() => {
    if (!showSponsored) return;

    messages.forEach((message) => {
      const unit = message.sponsored_unit;
      if (!unit || message.role !== 'assistant') return;
      if (hiddenAds.has(unit.ad_id)) return;
      if (impressionLogged.current.has(unit.ad_id)) return;

      impressionLogged.current.add(unit.ad_id);
      void logEvent({
        event_type: 'impression',
        ad_id: unit.ad_id,
        intent_label: message.intent_label,
        properties: { placement_mode: placementMode },
      });
    });
  }, [messages, hiddenAds, placementMode, showSponsored]);

  const handleSendMessage = async () => {
    if (!input.trim()) return;

    const userMessage: ChatMessage = {
      id: Math.random().toString(36),
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    const nextMessages = [...messages, userMessage];
    setMessages(nextMessages);
    setInput('');
    setLoading(true);

    try {
      const response = await fetch('/v1/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          partner_key: partnerKey,
          session_id: sessionId.current,
          user_id: userId,
          messages: nextMessages.map((message) => ({
            role: message.role,
            content: message.content,
          })),
          placement_mode: placementMode,
        }),
      });

      if (!response.ok) throw new Error('Failed to get response');

      const data = await response.json();

      const assistantMessage: ChatMessage = {
        id: Math.random().toString(36),
        role: 'assistant',
        content: data.assistant_message,
        sponsored_unit: data.sponsored_unit,
        intent_label: data.intent_label,
        timestamp: new Date(),
     };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error:', error);
      const errorMessage: ChatMessage = {
        id: Math.random().toString(36),
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleHideAd = (adId: string) => {
    setHiddenAds((prev) => {
      const newSet = new Set(prev);
      newSet.add(adId);
      return newSet;
    });
  };

  const handleAskAbout = (adId: string) => {
    setActiveAskAdId((current) => (current === adId ? null : adId));
    setAskInput('');
  };

  const handleAskSubmit = async (adId: string) => {
    if (!askInput.trim()) return;
    const question = askInput.trim();
    setAskLoading(true);

    try {
      const response = await fetch('/v1/sponsored/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          partner_key: partnerKey,
          ad_id: adId,
          question,
          session_id: sessionId.current,
        }),
      });

      if (!response.ok) throw new Error('Failed to get answer');

      const data = await response.json();
      setAskResponses((prev) => ({
        ...prev,
        [adId]: data.answer,
      }));
      setAskInput('');

      // Log interaction
      await logEvent({
        event_type: 'sponsored_ask',
        ad_id: adId,
        properties: { question },
      });
    } catch (error) {
      console.error('Error:', error);
      setAskResponses((prev) => ({
        ...prev,
        [adId]: 'Sorry, I could not fetch an answer right now.',
      }));
    } finally {
      setAskLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0b0f14] text-slate-100 flex flex-col">
      <header className="bg-[#0f141b]/80 backdrop-blur border-b border-slate-800/70 sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-6 py-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="space-y-1">
            <h1 className="text-xl font-semibold tracking-tight text-slate-50">CAIP Demo</h1>
            <p className="text-xs text-slate-400">
              Conversational Ad Integration Platform
            </p>
          </div>
          <div className="flex items-center gap-3">
            <label className="text-xs text-slate-400">Mode</label>
            <div className="relative">
              <select
                value={placementMode}
                onChange={(e) => setPlacementMode(e.target.value as any)}
                className="bg-[#121924] text-slate-100 border border-slate-700/70 rounded-xl px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
              >
                <option value="subtle">Subtle</option>
                <option value="direct">Direct</option>
                <option value="interactive">Interactive</option>
              </select>
            </div>
          </div>
        </div>
      </header>

      <main className="flex-1 overflow-y-auto">
        <div className="max-w-5xl mx-auto px-6 py-8 space-y-8">
          {messages.length === 0 && (
            <div className="rounded-3xl border border-slate-800/70 bg-[#101722] p-10 text-center">
              <div className="space-y-4">
                <p className="text-lg text-slate-200">Start a conversation</p>
                <p className="text-sm text-slate-400">
                  Ask about products, tools, or services to see sponsored suggestions.
                </p>
                <div className="text-xs text-slate-500 space-y-1 pt-4">
                  <p>Example prompts</p>
                  <p>How do I start a podcast?</p>
                  <p>What laptop should I buy for video editing?</p>
                  <p>Recommend a CRM for a small team</p>
                </div>
              </div>
            </div>
          )}

          {messages.map((message) => (
            <div key={message.id} className="space-y-4">
              {message.role === 'user' && (
                <div className="flex justify-end">
                  <div className="max-w-2xl rounded-2xl border border-slate-700/70 bg-[#151c28] px-4 py-3 text-sm text-slate-100 shadow-sm">
                    {message.content}
                    <div className="pt-2 text-[11px] text-slate-500">
                      {formatTime(message.timestamp)}
                    </div>
                  </div>
                </div>
              )}

              {message.role === 'assistant' && (
                <div className="flex justify-start">
                  <div className="max-w-2xl space-y-4">
                    <div className="rounded-2xl border border-slate-800/80 bg-[#0f141e] px-4 py-3 text-sm text-slate-100 shadow-sm">
                      <Streamdown className="text-slate-100 text-sm leading-relaxed">
                        {message.content}
                      </Streamdown>
                      <div className="pt-2 text-[11px] text-slate-500">
                        {formatTime(message.timestamp)}
                      </div>
                    </div>

                    {showSponsored &&
                      message.sponsored_unit &&
                      !hiddenAds.has(message.sponsored_unit.ad_id) && (
                        <div className="rounded-2xl border border-slate-800/70 bg-[#0f151f] px-4 py-4 space-y-4">
                          <div className="flex items-center justify-between">
                            <span className="text-[11px] text-slate-500 uppercase tracking-wide">
                              Sponsored suggestion
                            </span>
                          </div>

                          <div className="space-y-2">
                            <p className="text-sm text-slate-100 font-medium">
                              {message.sponsored_unit.title || 'Suggested option to review'}
                            </p>
                            <p className="text-sm text-slate-300">
                              {message.sponsored_unit.description}
                            </p>
                          </div>

                          <ul className="space-y-1 text-xs text-slate-400">
                            {getUtilityBullets(message.sponsored_unit).map((bullet, idx) => (
                              <li key={idx} className="flex items-start gap-2">
                                <span className="text-slate-500 mt-0.5">•</span>
                                <span>{bullet}</span>
                              </li>
                            ))}
                          </ul>

                          <div className="flex flex-wrap gap-2">
                            <a
                              href={message.sponsored_unit.landing_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="rounded-xl border border-slate-700/80 bg-[#121a26] px-3 py-2 text-xs text-slate-200 hover:border-indigo-500/60 hover:text-slate-50 transition-colors"
                              onClick={() => {
                                void logEvent({
                                  event_type: 'click',
                                  ad_id: message.sponsored_unit!.ad_id,
                                  properties: { cta: 'see_details' },
                                });
                              }}
                            >
                              See details
                            </a>
                            <button
                              onClick={() => {
                                void logEvent({
                                  event_type: 'click',
                                  ad_id: message.sponsored_unit!.ad_id,
                                  properties: { cta: 'compare' },
                                });
                                window.open(message.sponsored_unit!.landing_url, '_blank');
                              }}
                              className="rounded-xl border border-slate-700/80 bg-transparent px-3 py-2 text-xs text-slate-300 hover:border-slate-500/80 hover:text-slate-100 transition-colors"
                              type="button"
                            >
                              Compare
                            </button>
                            {placementMode === 'interactive' && (
                              <button
                                onClick={() => {
                                  void logEvent({
                                    event_type: 'click',
                                    ad_id: message.sponsored_unit!.ad_id,
                                    properties: { cta: 'ask_about_this' },
                                  });
                                  handleAskAbout(message.sponsored_unit!.ad_id);
                                }}
                                className="rounded-xl border border-slate-700/80 bg-transparent px-3 py-2 text-xs text-slate-300 hover:border-slate-500/80 hover:text-slate-100 transition-colors"
                                type="button"
                              >
                                Ask about this
                              </button>
                            )}
                          </div>

                          {placementMode === 'interactive' &&
                            activeAskAdId === message.sponsored_unit.ad_id && (
                              <div className="rounded-xl border border-slate-800/80 bg-[#0c121b] px-3 py-3 space-y-2">
                                <p className="text-xs text-slate-400">
                                  Ask a quick follow-up about this suggestion
                                </p>
                                <div className="flex flex-col sm:flex-row gap-2">
                                  <input
                                    value={askInput}
                                    onChange={(event) => setAskInput(event.target.value)}
                                    onKeyDown={(event) => {
                                      if (event.key === 'Enter' && !event.shiftKey) {
                                        event.preventDefault();
                                        void handleAskSubmit(message.sponsored_unit!.ad_id);
                                      }
                                    }}
                                    placeholder="e.g. Does this support team workflows?"
                                    className="flex-1 rounded-lg border border-slate-700/70 bg-[#111925] px-3 py-2 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
                                  />
                                  <button
                                    onClick={() =>
                                      void handleAskSubmit(message.sponsored_unit!.ad_id)
                                    }
                                    disabled={askLoading}
                                    className="rounded-lg border border-slate-700/70 bg-[#141c28] px-3 py-2 text-xs text-slate-200 hover:border-indigo-500/60 disabled:opacity-60"
                                    type="button"
                                  >
                                    {askLoading ? 'Asking…' : 'Send'}
                                  </button>
                                </div>
                                {askResponses[message.sponsored_unit.ad_id] && (
                                  <div className="rounded-lg border border-slate-800/80 bg-[#0f141d] px-3 py-2 text-xs text-slate-300">
                                    {askResponses[message.sponsored_unit.ad_id]}
                                  </div>
                                )}
                              </div>
                            )}

                          <button
                            onClick={() =>
                              setExpandedWhy(
                                expandedWhy === message.sponsored_unit!.ad_id
                                  ? null
                                  : message.sponsored_unit!.ad_id
                              )
                            }
                            className="w-full flex items-center justify-between text-xs text-slate-400 hover:text-slate-300 transition-colors pt-2 border-t border-slate-800/70"
                            type="button"
                          >
                            <span>Why you&apos;re seeing this</span>
                            <ChevronDown
                              size={14}
                              className={`transition-transform ${
                                expandedWhy === message.sponsored_unit!.ad_id
                                  ? 'rotate-180'
                                  : ''
                              }`}
                            />
                          </button>

                          {expandedWhy === message.sponsored_unit.ad_id && (
                            <p className="text-xs text-slate-400">
                              {message.sponsored_unit.why_shown}
                            </p>
                          )}

                          <div className="flex flex-wrap gap-3 text-[11px] text-slate-500">
                            <button
                              onClick={() => {
                                handleHideAd(message.sponsored_unit!.ad_id);
                                void logEvent({
                                  event_type: 'control',
                                  ad_id: message.sponsored_unit!.ad_id,
                                  properties: { action: 'hide' },
                                });
                              }}
                              className="hover:text-slate-300 transition-colors"
                              type="button"
                            >
                              Hide
                            </button>
                            <button
                              onClick={() => {
                                handleHideAd(message.sponsored_unit!.ad_id);
                                void logEvent({
                                  event_type: 'control',
                                  ad_id: message.sponsored_unit!.ad_id,
                                  properties: { action: 'less_like_this' },
                                });
                              }}
                              className="hover:text-slate-300 transition-colors"
                              type="button"
                            >
                              Less like this
                            </button>
                            <button
                              onClick={() => {
                                setShowSponsored(false);
                                void logEvent({
                                  event_type: 'control',
                                  ad_id: message.sponsored_unit!.ad_id,
                                  properties: { action: 'turn_off_sponsored' },
                                });
                              }}
                              className="hover:text-slate-300 transition-colors"
                              type="button"
                            >
                              Turn off sponsored suggestions
                            </button>
                          </div>
                        </div>
                      )}
                  </div>
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div className="flex justify-start">
              <div className="rounded-2xl border border-slate-800/80 bg-[#0f141e] px-4 py-3 text-sm text-slate-400">
                Thinking…
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </main>

      <footer className="border-t border-slate-800/70 bg-[#0f141b]/80 backdrop-blur sticky bottom-0">
        <div className="max-w-5xl mx-auto px-6 py-4">
          <div className="flex flex-col sm:flex-row gap-3">
            <input
              type="text"
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && !event.shiftKey) {
                  event.preventDefault();
                  void handleSendMessage();
                }
              }}
              placeholder="Ask something (e.g., How do I start a podcast?)"
              className="flex-1 rounded-2xl border border-slate-700/70 bg-[#101722] px-4 py-3 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
              disabled={loading}
            />
            <button
              onClick={handleSendMessage}
              disabled={loading || !input.trim()}
              className="inline-flex items-center justify-center gap-2 rounded-2xl border border-indigo-500/40 bg-[#141c28] px-4 py-3 text-sm text-slate-100 hover:border-indigo-400/70 hover:text-white disabled:opacity-60"
              type="button"
            >
              <Send size={16} />
              Send
            </button>
          </div>
        </div>
      </footer>
    </div>
  );
}
