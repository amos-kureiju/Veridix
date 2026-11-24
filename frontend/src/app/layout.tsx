import type { Metadata } from "next";
import Script from "next/script";
import { UserSidebarProvider } from "@/components/layout/UserSidebarProvider";
import "./globals.css";

export const metadata: Metadata = {
    title: "VERIDIX — AI Political Disinformation Intelligence",
    description: "Sistem deteksi disinformasi politik berbasis IndoBERT, LIME XAI, dan PaddleOCR.",
    icons: {
        icon: "/logo.png",
    },
};

const stripExtensionAttrScript = `
(function () {
  var ATTR = "bis_skin_checked";
  function cleanNode(node) {
    if (!node || node.nodeType !== 1) return;
    if (node.hasAttribute(ATTR)) node.removeAttribute(ATTR);
    var nested = node.querySelectorAll ? node.querySelectorAll("[" + ATTR + "]") : [];
    for (var i = 0; i < nested.length; i++) nested[i].removeAttribute(ATTR);
  }
  cleanNode(document.documentElement);
  if (typeof MutationObserver !== "function") return;
  var observer = new MutationObserver(function (mutations) {
    for (var i = 0; i < mutations.length; i++) {
      var m = mutations[i];
      if (m.type === "attributes" && m.target && m.target.removeAttribute) {
        m.target.removeAttribute(ATTR);
      } else if (m.type === "childList") {
        for (var j = 0; j < m.addedNodes.length; j++) {
          cleanNode(m.addedNodes[j]);
        }
      }
    }
  });
  observer.observe(document.documentElement, {
    attributes: true,
    childList: true,
    subtree: true,
    attributeFilter: [ATTR]
  });
  function stop() {
    observer.disconnect();
  }
  if (document.readyState === "complete") {
    setTimeout(stop, 2000);
  } else {
    window.addEventListener("load", function () {
      cleanNode(document.documentElement);
      setTimeout(stop, 2000);
    }, { once: true });
    setTimeout(stop, 8000);
  }
})();
`;

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="id" suppressHydrationWarning>
            <body className="bg-[#f1f5f5] text-slate-800 antialiased min-h-screen" suppressHydrationWarning>
                <Script id="strip-extension-attrs" strategy="beforeInteractive">
                    {stripExtensionAttrScript}
                </Script>
                <UserSidebarProvider>{children}</UserSidebarProvider>
            </body>
        </html>
    );
}
