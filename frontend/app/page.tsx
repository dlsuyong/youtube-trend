"use client";

import { useEffect, useState } from "react";

interface Video {
  id: string;
  title: string;
  channel: string;
  thumbnail: string;
  publishedAt: string;
  views: number;
  likes: number;
  comments: number;
  score: number;
  url: string;
}

interface Category {
  categoryId: string;
  categoryName: string;
  videos: Video[];
}

type SortKey = "score" | "views" | "likes" | "publishedAt";

export default function Home() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [activeTab, setActiveTab] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [updatedAt, setUpdatedAt] = useState<string>("");
  const [sortKey, setSortKey] = useState<SortKey>("score");
  const [darkMode, setDarkMode] = useState(true);
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  useEffect(() => {
    fetch("http://localhost:8000/api/trending")
      .then((res) => res.json())
      .then((data) => {
        setCategories(data.categories);
        setActiveTab(data.categories[0]?.categoryId || "");
        setUpdatedAt(data.updatedAt || "");
        setLoading(false);
      });
  }, []);

  const activeCategory = categories.find((c) => c.categoryId === activeTab);
  const isShorts = activeTab === "shorts";

  const sortedVideos = activeCategory
    ? [...activeCategory.videos].sort((a, b) => {
        if (sortKey === "publishedAt")
          return new Date(b.publishedAt).getTime() - new Date(a.publishedAt).getTime();
        return b[sortKey] - a[sortKey];
      })
    : [];

  const formatNumber = (n: number) => {
    if (n >= 100000000) return `${(n / 100000000).toFixed(1)}억`;
    if (n >= 10000) return `${(n / 10000).toFixed(1)}만`;
    return n.toLocaleString();
  };

  const timeAgo = (dateStr: string) => {
    const diff = (Date.now() - new Date(dateStr).getTime()) / 1000;
    if (diff < 3600) return `${Math.floor(diff / 60)}분 전`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}시간 전`;
    return `${Math.floor(diff / 86400)}일 전`;
  };

  const bg = darkMode ? "bg-gray-950" : "bg-gray-100";
  const headerBg = darkMode ? "bg-gray-900 border-gray-800" : "bg-white border-gray-200";
  const tabBg = darkMode ? "bg-gray-900 border-gray-800" : "bg-white border-gray-200";
  const cardBg = darkMode ? "bg-gray-900 hover:bg-gray-800" : "bg-white hover:bg-gray-50 border border-gray-200";
  const textMain = darkMode ? "text-white" : "text-gray-900";
  const textSub = darkMode ? "text-gray-400" : "text-gray-500";
  const textMuted = darkMode ? "text-gray-500" : "text-gray-400";
  const selectBg = darkMode ? "bg-gray-800 text-white border-gray-700" : "bg-white text-gray-900 border-gray-300";

  if (loading) {
    return (
      <div className={`min-h-screen ${bg} flex items-center justify-center`}>
        {/* 스켈레톤 로딩 */}
        <div className="w-full max-w-6xl px-6">
          <div className="h-8 bg-gray-800 rounded w-48 mb-4 animate-pulse" />
          <div className="flex gap-2 mb-6">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-8 bg-gray-800 rounded w-24 animate-pulse" />
            ))}
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="bg-gray-900 rounded-xl overflow-hidden animate-pulse">
                <div className="w-full aspect-video bg-gray-800" />
                <div className="p-3 space-y-2">
                  <div className="h-4 bg-gray-800 rounded w-full" />
                  <div className="h-4 bg-gray-800 rounded w-3/4" />
                  <div className="h-3 bg-gray-800 rounded w-1/2" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`min-h-screen ${bg} ${textMain}`}>
      {/* 헤더 */}
      <header className={`${headerBg} border-b px-6 py-4 flex items-center justify-between`}>
        <div>
          <h1 className="text-2xl font-bold text-red-500">🔥 유튜브 트렌드</h1>
          <p className={`${textSub} text-sm mt-1`}>
            커스텀 알고리즘으로 선별한 지금 뜨는 영상
            {updatedAt && (
              <span className={`ml-3 ${textMuted} text-xs`}>마지막 업데이트: {updatedAt}</span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* 정렬 선택 */}
          <select
            value={sortKey}
            onChange={(e) => setSortKey(e.target.value as SortKey)}
            className={`text-sm px-3 py-2 rounded-lg border ${selectBg} outline-none`}
          >
            <option value="score">🏆 커스텀 점수순</option>
            <option value="views">👁 조회수순</option>
            <option value="likes">👍 좋아요순</option>
            <option value="publishedAt">🕐 최신순</option>
          </select>

          {/* 다크/라이트 모드 */}
          <button
            onClick={() => setDarkMode(!darkMode)}
            className={`px-3 py-2 rounded-lg text-sm border ${selectBg}`}
          >
            {darkMode ? "☀️ 라이트" : "🌙 다크"}
          </button>
        </div>
      </header>

      {/* 카테고리 탭 */}
      <div className={`overflow-x-auto ${tabBg} border-b`}>
        <div className="flex px-4 gap-1 min-w-max">
          {categories.map((cat) => (
            <button
              key={cat.categoryId}
              onClick={() => setActiveTab(cat.categoryId)}
              className={`px-4 py-3 text-sm font-medium whitespace-nowrap transition-colors ${
                activeTab === cat.categoryId
                  ? "text-red-500 border-b-2 border-red-500"
                  : `${textSub} hover:${textMain}`
              }`}
            >
              {cat.categoryName}
            </button>
          ))}
        </div>
      </div>

      {/* 영상 그리드 */}
      <main className="px-6 py-6">
        <div
          className={
            isShorts
              ? "grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-4"
              : "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4"
          }
        >
          {sortedVideos.map((video, index) => (
            <a
              key={video.id}
              href={video.url}
              target="_blank"
              rel="noopener noreferrer"
              className={`${cardBg} rounded-xl overflow-hidden transition-all duration-200 group relative ${
                hoveredId === video.id ? "ring-2 ring-red-500 scale-105 z-10" : ""
              }`}
              onMouseEnter={() => setHoveredId(video.id)}
              onMouseLeave={() => setHoveredId(null)}
            >
              {/* 썸네일 */}
              <div className={`relative ${isShorts ? "aspect-[9/16]" : "aspect-video"} overflow-hidden`}>
                <img
                  src={video.thumbnail}
                  alt={video.title}
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200"
                />
                <span className="absolute top-2 left-2 bg-red-500 text-white text-xs font-bold px-2 py-1 rounded">
                  {index + 1}위
                </span>
              </div>

              {/* 정보 */}
              <div className="p-3">
                <h2 className={`text-sm font-semibold line-clamp-2 group-hover:text-red-400 transition-colors ${textMain}`}>
                  {video.title}
                </h2>
                <p className={`${textSub} text-xs mt-1`}>{video.channel}</p>
                <p className={`${textMuted} text-xs mt-1`}>{timeAgo(video.publishedAt)}</p>

                
                
                <div className={`mt-2 pt-2 border-t ${darkMode ? "border-gray-700" : "border-gray-200"} flex gap-3 text-xs ${textSub}`}>
                  <span>👁 {formatNumber(video.views)}</span>
                  <span>👍 {formatNumber(video.likes)}</span>
                  <span>💬 {formatNumber(video.comments)}</span>
                </div>
                
              </div>
            </a>
          ))}
        </div>
      </main>
    </div>
  );
}