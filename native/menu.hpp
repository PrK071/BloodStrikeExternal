// C++ / native/menu.hpp / Windows x64 / aeon native interface
#pragma once
namespace theme {
constexpr COLORREF rgb(unsigned hex){return RGB((hex>>16)&255,(hex>>8)&255,hex&255);}
constexpr auto ground=rgb(0x0d0c10),rail=rgb(0x111015),surface=rgb(0x151219),footer=rgb(0x0f0d12),field=rgb(0x100d14);
constexpr auto button=rgb(0x1a151f),hover=rgb(0x2d2332),navHover=rgb(0x211a27),selected=rgb(0x342838),actionHover=rgb(0x403147);
constexpr auto plum=rgb(0x756079),focus=rgb(0xb7a1bd),text=rgb(0xe3dad4),secondary=rgb(0xada1ad),divider=rgb(0x302833),border=rgb(0x43394a),fieldBorder=rgb(0x39303f),rose=rgb(0xb86a68),sage=rgb(0xa4b39b);
}
std::array<HWND,6> checks{};std::array<HWND,3> navigation{};
HWND radiusEdit=nullptr,speedEdit=nullptr,smoothEdit=nullptr;std::array<HWND,2> targetButtons{};HFONT menuFont=nullptr,brandFont=nullptr,smallFont=nullptr;
int currentPage=0;HWND hoveredControl=nullptr;
HBRUSH fieldBrush=nullptr;
struct BrandTypeface {
 fs::path brand=appDir/L"fonts"/L"MomsTypewriter.ttf",body=appDir/L"fonts"/L"Poppins-Medium.ttf";
 BrandTypeface(){require(AddFontResourceExW(brand.c_str(),FR_PRIVATE,nullptr)>0,"Mom's Typewriter font missing");require(AddFontResourceExW(body.c_str(),FR_PRIVATE,nullptr)>0,"Poppins font missing");}
 ~BrandTypeface(){RemoveFontResourceExW(brand.c_str(),FR_PRIVATE,nullptr);RemoveFontResourceExW(body.c_str(),FR_PRIVATE,nullptr);}
};
std::array<std::atomic<bool>*,6> toggles{&settings.aim,&settings.esp,&settings.boxes,&settings.bones,&settings.tracers,&settings.labels};
void fill(HDC dc,RECT rect,COLORREF color){HBRUSH b=CreateSolidBrush(color);FillRect(dc,&rect,b);DeleteObject(b);}
void stroke(HDC dc,RECT rect,COLORREF color,int radius=0){HPEN p=CreatePen(PS_SOLID,1,color);auto old=SelectObject(dc,p),brush=SelectObject(dc,GetStockObject(NULL_BRUSH));if(radius)RoundRect(dc,rect.left,rect.top,rect.right,rect.bottom,radius,radius);else Rectangle(dc,rect.left,rect.top,rect.right,rect.bottom);SelectObject(dc,brush);SelectObject(dc,old);DeleteObject(p);}
void copyText(HDC dc,RECT rect,const std::wstring& value,COLORREF color,HFONT font,UINT format=DT_LEFT|DT_VCENTER|DT_SINGLELINE|DT_END_ELLIPSIS){auto old=SelectObject(dc,font);SetBkMode(dc,TRANSPARENT);SetTextColor(dc,color);DrawTextW(dc,value.c_str(),int(value.size()),&rect,format);SelectObject(dc,old);}
void segment(HDC dc,int x,int y,int xx,int yy,COLORREF color,int width=1){HPEN pen=CreatePen(PS_SOLID,width,color);auto old=SelectObject(dc,pen);MoveToEx(dc,x,y,nullptr);LineTo(dc,xx,yy);SelectObject(dc,old);DeleteObject(pen);}
void panel(HDC dc,RECT r,const wchar_t* title){fill(dc,r,theme::surface);stroke(dc,r,theme::divider);segment(dc,r.left,r.top+30,r.right,r.top+30,theme::divider);copyText(dc,{r.left+12,r.top,r.right-12,r.top+30},title,theme::text,menuFont);}
void updatePage(HWND hwnd){
 for(size_t i=0;i<checks.size();++i)ShowWindow(checks[i],(i==0?currentPage==0:currentPage==1)?SW_SHOW:SW_HIDE);
 ShowWindow(radiusEdit,currentPage==2?SW_SHOW:SW_HIDE);ShowWindow(speedEdit,currentPage==2?SW_SHOW:SW_HIDE);
 ShowWindow(smoothEdit,currentPage==0?SW_SHOW:SW_HIDE);for(HWND button:targetButtons)ShowWindow(button,currentPage==0?SW_SHOW:SW_HIDE);
 InvalidateRect(hwnd,nullptr,FALSE);for(auto button:navigation)InvalidateRect(button,nullptr,FALSE);
}
LRESULT CALLBACK hoverProc(HWND hwnd,UINT msg,WPARAM wp,LPARAM lp,UINT_PTR,DWORD_PTR){
 if(msg==WM_MOUSEMOVE&&hoveredControl!=hwnd){HWND previous=hoveredControl;hoveredControl=hwnd;if(previous)InvalidateRect(previous,nullptr,FALSE);InvalidateRect(hwnd,nullptr,FALSE);TRACKMOUSEEVENT track{sizeof(track),TME_LEAVE,hwnd,0};TrackMouseEvent(&track);}
 if(msg==WM_MOUSELEAVE){hoveredControl=nullptr;InvalidateRect(hwnd,nullptr,FALSE);}
 return DefSubclassProc(hwnd,msg,wp,lp);
}
void paintMenu(HDC dc){
 fill(dc,{0,0,770,557},theme::ground);fill(dc,{0,0,168,557},theme::rail);
 for(int y=63;y<527;y+=14)for(int x=182;x<756;x+=14)SetPixelV(dc,x,y,theme::navHover);
 stroke(dc,{0,0,770,557},theme::border);segment(dc,167,0,167,557,theme::divider);
 copyText(dc,{14,7,154,43},L"aeon",theme::text,brandFont,DT_CENTER|DT_VCENTER|DT_SINGLELINE);
 copyText(dc,{14,38,154,55},L"painel local",theme::secondary,smallFont,DT_CENTER|DT_VCENTER|DT_SINGLELINE);
 fill(dc,{184,16,366,50},theme::surface);stroke(dc,{184,16,366,50},theme::divider,6);
 fill(dc,{188,20,362,46},theme::selected);
 const wchar_t* tabs[]={L"mira",L"jogadores",L"geral"};copyText(dc,{198,20,352,46},tabs[currentPage],theme::text,menuFont);
 copyText(dc,{184,66,754,92},currentPage==0?L"combate":currentPage==1?L"visuais":L"ajustes",theme::focus,menuFont);
 if(currentPage==0){
  panel(dc,{184,100,534,358},L"mira");
  copyText(dc,{196,178,522,200},L"ponto de mira",theme::secondary,menuFont);
  copyText(dc,{196,247,522,273},L"ativação: botão direito segurado",theme::secondary,menuFont);
  copyText(dc,{196,286,425,312},L"suavidade (ms)",theme::text,menuFont);
  fill(dc,{438,286,518,311},theme::field);stroke(dc,{438,286,518,311},theme::fieldBorder);copyText(dc,{438,286,518,311},std::to_wstring(settings.smoothMs.load()),theme::text,menuFont,DT_CENTER|DT_VCENTER|DT_SINGLELINE);
  copyText(dc,{196,322,522,346},L"0 = direto / maior = mais suave",theme::secondary,smallFont);
  panel(dc,{546,100,754,268},L"estado");
  copyText(dc,{558,143,742,170},settings.aim?L"mira habilitada":L"mira desabilitada",settings.aim?theme::sage:theme::secondary,menuFont);
  copyText(dc,{558,180,742,246},L"a ativação exige foco no jogo e calibração válida.",theme::secondary,smallFont,DT_LEFT|DT_WORDBREAK);
 }else if(currentPage==1){
  panel(dc,{184,100,534,349},L"elementos do esp");panel(dc,{546,100,754,438},L"prévia");
  // This is a code-drawn illustration of the selected decorations, not live telemetry.
  int cx=650;COLORREF ink=settings.esp?theme::focus:theme::border;
  stroke(dc,{636,167,664,195},ink,28);segment(dc,cx,195,cx,281,ink);segment(dc,650,211,615,250,ink);segment(dc,650,211,685,250,ink);segment(dc,650,281,623,337,ink);segment(dc,650,281,677,337,ink);
  if(settings.esp&&settings.boxes)stroke(dc,{609,159,691,344},theme::plum);
  if(settings.esp&&settings.bones){segment(dc,650,194,650,281,theme::text,2);segment(dc,650,211,615,250,theme::text);segment(dc,650,211,685,250,theme::text);segment(dc,650,281,623,337,theme::text);segment(dc,650,281,677,337,theme::text);}
  if(settings.esp&&settings.tracers)segment(dc,650,393,650,344,theme::plum);
  if(settings.esp&&settings.labels)copyText(dc,{592,133,708,156},L"hp",theme::text,smallFont,DT_CENTER|DT_SINGLELINE|DT_VCENTER);
  copyText(dc,{558,407,742,429},L"prévia ilustrativa",theme::secondary,smallFont,DT_CENTER|DT_SINGLELINE|DT_VCENTER);
 }else{
  panel(dc,{184,100,534,286},L"mira / resposta");
  copyText(dc,{196,146,425,172},L"raio de aquisição (px)",theme::text,menuFont);
  copyText(dc,{196,190,425,216},L"velocidade (contagens)",theme::text,menuFont);
  copyText(dc,{196,239,522,268},L"alterações são salvas automaticamente",theme::secondary,smallFont);
  panel(dc,{546,100,754,286},L"atalhos");
  copyText(dc,{558,146,742,177},L"insert / menu",theme::text,menuFont);copyText(dc,{558,190,742,221},L"f8 / encerrar",theme::text,menuFont);
 }
 fill(dc,{14,487,154,541},theme::surface);stroke(dc,{14,487,154,541},theme::divider,6);
 copyText(dc,{26,493,142,516},L"sessão local",theme::text,menuFont);copyText(dc,{26,516,142,535},L"insert / menu",theme::secondary,smallFont);
 fill(dc,{168,527,770,557},theme::footer);segment(dc,168,527,770,527,theme::divider);
 std::wstring runtime;{std::lock_guard lock(statusMutex);runtime=statusText;}if(runtime.starts_with(L"C++ | "))runtime.erase(0,6);
 copyText(dc,{184,531,633,553},runtime,theme::secondary,smallFont);copyText(dc,{636,531,754,553},L"f8 / encerrar",theme::secondary,smallFont,DT_RIGHT|DT_SINGLELINE|DT_VCENTER);
}
LRESULT CALLBACK menuProc(HWND hwnd,UINT msg,WPARAM wp,LPARAM lp){
 switch(msg){
 case WM_CREATE:{
  menuWindow=hwnd;InitCommonControls();fieldBrush=CreateSolidBrush(theme::field);
  menuFont=CreateFontW(-13,0,0,0,FW_MEDIUM,FALSE,FALSE,FALSE,DEFAULT_CHARSET,OUT_TT_PRECIS,CLIP_DEFAULT_PRECIS,CLEARTYPE_QUALITY,DEFAULT_PITCH,L"Poppins Medium");
  smallFont=CreateFontW(-11,0,0,0,FW_MEDIUM,FALSE,FALSE,FALSE,DEFAULT_CHARSET,OUT_TT_PRECIS,CLIP_DEFAULT_PRECIS,CLEARTYPE_QUALITY,DEFAULT_PITCH,L"Poppins Medium");
  brandFont=CreateFontW(-24,0,0,0,FW_NORMAL,FALSE,FALSE,FALSE,DEFAULT_CHARSET,OUT_TT_PRECIS,CLIP_DEFAULT_PRECIS,ANTIALIASED_QUALITY,DEFAULT_PITCH,L"Mom\u00b4sTypewriter");
  HDC dc=CreateCompatibleDC(nullptr);auto old=SelectObject(dc,brandFont);wchar_t face[128]{};GetTextFaceW(dc,128,face);require(!wcscmp(face,L"Mom\u00b4sTypewriter"),"brand font substitution");SelectObject(dc,menuFont);GetTextFaceW(dc,128,face);require(!wcscmp(face,L"Poppins Medium")||!wcscmp(face,L"Poppins"),"body font substitution");SelectObject(dc,old);DeleteDC(dc);
  atomicFile(appDir/L"branding.json","{\"name\":\"aeon\",\"brand_font\":\"Mom\\u00b4sTypewriter\",\"body_font\":\"Poppins Medium\",\"font_loaded\":true,\"theme\":\"plum\"}\n");
  auto make=[&](int id,const wchar_t* text,int x,int y,int w,int h){HWND control=CreateWindowW(L"BUTTON",text,WS_CHILD|WS_VISIBLE|WS_TABSTOP|BS_OWNERDRAW,x,y,w,h,hwnd,reinterpret_cast<HMENU>(id),nullptr,nullptr);require(control!=nullptr,"button creation");SetWindowSubclass(control,hoverProc,1,0);return control;};
  const wchar_t* nav[]={L"combate",L"visuais",L"ajustes"};for(int i=0;i<3;++i)navigation[i]=make(300+i,nav[i],14,62+i*39,140,35);
  const wchar_t* names[]={L"habilitar mira",L"habilitar esp",L"caixas",L"skeleton",L"antena",L"hp"};for(int i=0;i<6;++i)checks[i]=make(100+i,names[i],196,i==0?143:143+(i-1)*38,326,30);
  make(400,L"minimizar",684,17,30,28);make(401,L"fechar",719,17,30,28);
  auto edit=[&](int id,int y,int value){HWND e=CreateWindowExW(0,L"EDIT",std::to_wstring(value).c_str(),WS_CHILD|WS_TABSTOP|ES_NUMBER|ES_CENTER|WS_BORDER,438,y,80,25,hwnd,reinterpret_cast<HMENU>(id),nullptr,nullptr);SendMessageW(e,WM_SETFONT,reinterpret_cast<WPARAM>(menuFont),TRUE);return e;};
  radiusEdit=edit(200,146,settings.radius);speedEdit=edit(201,190,settings.speed);
  smoothEdit=edit(202,286,settings.smoothMs);
  targetButtons[0]=make(500,L"cabeça (estim.)",196,208,156,28);targetButtons[1]=make(501,L"corpo",366,208,156,28);
  RegisterHotKey(hwnd,1,MOD_NOREPEAT,VK_INSERT);RegisterHotKey(hwnd,2,MOD_NOREPEAT,VK_F8);SetTimer(hwnd,1,500,nullptr);updatePage(hwnd);return 0;
 }
 case WM_DRAWITEM:{
  auto& d=*reinterpret_cast<DRAWITEMSTRUCT*>(lp);HDC dc=d.hDC;RECT r=d.rcItem;int id=int(d.CtlID);bool over=hoveredControl==d.hwndItem,focus=d.itemState&ODS_FOCUS;
  if(id>=300&&id<303){bool active=currentPage==id-300;fill(dc,r,active?theme::selected:over?theme::navHover:theme::rail);if(active)fill(dc,{r.left,r.top+7,r.left+2,r.bottom-7},theme::focus);wchar_t title[100]{};GetWindowTextW(d.hwndItem,title,100);copyText(dc,{r.left+16,r.top,r.right-8,r.bottom},title,theme::text,menuFont);}
  else if(id>=100&&id<106){fill(dc,r,over?theme::navHover:theme::surface);RECT box{r.left,r.top+7,r.left+15,r.top+22};bool on=toggles[id-100]->load();fill(dc,box,on?theme::plum:theme::field);stroke(dc,box,focus?theme::focus:theme::border,3);if(on){segment(dc,3,14,6,17,theme::text,2);segment(dc,6,17,12,10,theme::text,2);}wchar_t title[100]{};GetWindowTextW(d.hwndItem,title,100);copyText(dc,{r.left+25,r.top,r.right,r.bottom},title,theme::text,menuFont);}
  else if(id==500||id==501){bool active=(id==500)==settings.head.load();fill(dc,r,active?theme::selected:over?theme::hover:theme::button);stroke(dc,r,active?theme::focus:theme::border,4);wchar_t title[100]{};GetWindowTextW(d.hwndItem,title,100);copyText(dc,r,title,theme::text,menuFont,DT_CENTER|DT_VCENTER|DT_SINGLELINE);}
  else{fill(dc,r,id==401?(over?theme::rgb(0x5b2e39):theme::rgb(0x35232d)):(over?theme::hover:theme::button));if(id==400)segment(dc,10,17,20,17,theme::text);else{segment(dc,10,9,20,19,theme::text);segment(dc,20,9,10,19,theme::text);}}
  if(focus)stroke(dc,{r.left+1,r.top+1,r.right-1,r.bottom-1},theme::focus,4);return TRUE;
 }
 case WM_COMMAND:{int id=LOWORD(wp);
  if(id>=100&&id<106&&HIWORD(wp)==BN_CLICKED){auto& flag=*toggles[id-100];flag=!flag.load();saveSettings();InvalidateRect(reinterpret_cast<HWND>(lp),nullptr,FALSE);InvalidateRect(hwnd,nullptr,FALSE);}
  if(id>=300&&id<303&&HIWORD(wp)==BN_CLICKED){currentPage=id-300;updatePage(hwnd);}
  if((id==500||id==501)&&HIWORD(wp)==BN_CLICKED){settings.head=id==500;saveSettings();for(HWND button:targetButtons)InvalidateRect(button,nullptr,FALSE);}
  if(id==400)ShowWindow(hwnd,SW_MINIMIZE);if(id==401)PostMessageW(hwnd,WM_CLOSE,0,0);
  if(id>=200&&id<=202&&HIWORD(wp)==EN_CHANGE){wchar_t b[32]{};GetWindowTextW(reinterpret_cast<HWND>(lp),b,32);int n=_wtoi(b),max=id==200?4096:id==201?1000:500;if(n>=(id==202?0:1)&&n<=max){if(id==200)settings.radius=n;else if(id==201)settings.speed=n;else settings.smoothMs=n;saveSettings();}}
  if(id>=200&&id<=202&&HIWORD(wp)==EN_KILLFOCUS)SetWindowTextW(reinterpret_cast<HWND>(lp),std::to_wstring(id==200?settings.radius.load():id==201?settings.speed.load():settings.smoothMs.load()).c_str());return 0;
 }
 case WM_CTLCOLOREDIT:SetTextColor(reinterpret_cast<HDC>(wp),theme::text);SetBkColor(reinterpret_cast<HDC>(wp),theme::field);return reinterpret_cast<LRESULT>(fieldBrush);
 case WM_ERASEBKGND:return 1;
 case WM_PAINT:{PAINTSTRUCT ps;HDC dest=BeginPaint(hwnd,&ps),dc=CreateCompatibleDC(dest);HBITMAP b=CreateCompatibleBitmap(dest,770,557);auto old=SelectObject(dc,b);paintMenu(dc);BitBlt(dest,0,0,770,557,dc,0,0,SRCCOPY);SelectObject(dc,old);DeleteObject(b);DeleteDC(dc);EndPaint(hwnd,&ps);return 0;}
 case WM_PRINTCLIENT:paintMenu(reinterpret_cast<HDC>(wp));return 0;
 case WM_NCHITTEST:{POINT pt{short(LOWORD(lp)),short(HIWORD(lp))};ScreenToClient(hwnd,&pt);if(pt.y<56&&pt.x>168&&pt.x<675)return HTCAPTION;return HTCLIENT;}
 case WM_TIMER:{RECT footer{168,527,770,557};InvalidateRect(hwnd,&footer,FALSE);return 0;}
 case WM_HOTKEY:if(wp==1)ShowWindow(hwnd,IsWindowVisible(hwnd)?SW_HIDE:SW_SHOWNORMAL);else if(wp==2)PostMessageW(hwnd,WM_CLOSE,0,0);return 0;
 case WM_CLOSE:settings.running=false;saveSettings();DestroyWindow(hwnd);return 0;
 case WM_DESTROY:KillTimer(hwnd,1);UnregisterHotKey(hwnd,1);UnregisterHotKey(hwnd,2);if(fieldBrush)DeleteObject(fieldBrush);PostQuitMessage(0);return 0;
 }
 return DefWindowProcW(hwnd,msg,wp,lp);
}
void renderDesignPreview(){
 BrandTypeface fonts;WNDCLASSW wc{};wc.lpfnWndProc=menuProc;wc.hInstance=GetModuleHandleW(nullptr);wc.lpszClassName=L"Aeon.DesignPreview";require(RegisterClassW(&wc)!=0,"preview class");
 HWND window=CreateWindowW(wc.lpszClassName,L"aeon",WS_POPUP,0,0,770,557,nullptr,nullptr,wc.hInstance,nullptr);require(window!=nullptr,"preview window");
 currentPage=0;updatePage(window);{std::lock_guard lock(statusMutex);statusText=L"prévia do design / sessão desconectada";}
 HDC dc=CreateCompatibleDC(nullptr);BITMAPINFO info{};info.bmiHeader.biSize=40;info.bmiHeader.biWidth=770;info.bmiHeader.biHeight=-557;info.bmiHeader.biPlanes=1;info.bmiHeader.biBitCount=32;info.bmiHeader.biCompression=BI_RGB;void* pixels=nullptr;
 HBITMAP bitmap=CreateDIBSection(dc,&info,DIB_RGB_COLORS,&pixels,nullptr,0);require(bitmap!=nullptr,"preview bitmap");auto previous=SelectObject(dc,bitmap);
 SendMessageW(window,WM_PRINT,reinterpret_cast<WPARAM>(dc),PRF_CLIENT|PRF_CHILDREN|PRF_ERASEBKGND);
 BITMAPFILEHEADER file{};file.bfType=0x4d42;file.bfOffBits=sizeof(file)+sizeof(BITMAPINFOHEADER);file.bfSize=file.bfOffBits+770*557*4;
 std::ofstream output(appDir/L"design-preview.bmp",std::ios::binary);output.write(reinterpret_cast<char*>(&file),sizeof(file));output.write(reinterpret_cast<char*>(&info.bmiHeader),40);output.write(static_cast<char*>(pixels),770*557*4);output.close();
 SelectObject(dc,previous);DeleteObject(bitmap);DeleteDC(dc);DestroyWindow(window);DeleteObject(menuFont);DeleteObject(brandFont);DeleteObject(smallFont);
}
