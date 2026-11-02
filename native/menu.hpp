// C++ / native/menu.hpp / Windows x64 / aeon reference-style native interface
#pragma once
namespace theme {
constexpr COLORREF rgb(unsigned h){return RGB((h>>16)&255,(h>>8)&255,h&255);}
constexpr auto ground=rgb(0x0d0c10),rail=rgb(0x111015),surface=rgb(0x151219),footer=rgb(0x0f0d12),field=rgb(0x100d14);
constexpr auto button=rgb(0x1a151f),hover=rgb(0x2d2332),navHover=rgb(0x211a27),selected=rgb(0x342838);
constexpr auto plum=rgb(0x756079),focus=rgb(0xb7a1bd),text=rgb(0xe3dad4),secondary=rgb(0xada1ad),divider=rgb(0x302833),border=rgb(0x43394a),fieldBorder=rgb(0x39303f),rose=rgb(0xb86a68),sage=rgb(0xa4b39b);
}
constexpr int homePage=7;
int currentPage=homePage,uiWidth=900,uiHeight=606;
std::array<HWND,6> checks{};std::array<HWND,7> navigation{};std::array<HWND,2> targetButtons{};
HWND radiusEdit=nullptr,speedEdit=nullptr,smoothEdit=nullptr,hoveredControl=nullptr,logoButton=nullptr,languageButton=nullptr,buildButton=nullptr,returnButton=nullptr,footerBuild=nullptr,footerExit=nullptr;
std::array<HWND,3> windowButtons{};
HFONT menuFont=nullptr,brandFont=nullptr,smallFont=nullptr,navFont=nullptr,titleFont=nullptr,sectionFont=nullptr,actionFont=nullptr;
HBRUSH fieldBrush=nullptr;
std::vector<std::pair<std::wstring,Calibration>> displayedProfiles;
struct BrandTypeface {
 std::vector<fs::path> loaded;
 BrandTypeface(){
  for(auto filename:{L"TrixiePlain.otf",L"NarrowbandPrime.ttf",L"LoveLetterTypewriter.ttf"}){
   auto path=appDir/L"fonts"/filename;if(AddFontResourceExW(path.c_str(),FR_PRIVATE,nullptr)<=0){for(auto& old:loaded)RemoveFontResourceExW(old.c_str(),FR_PRIVATE,nullptr);throw std::runtime_error("reference font missing");}loaded.push_back(path);
  }
 }
 ~BrandTypeface(){for(auto& path:loaded)RemoveFontResourceExW(path.c_str(),FR_PRIVATE,nullptr);}
};
std::array<std::atomic<bool>*,6> toggles{&settings.aim,&settings.esp,&settings.boxes,&settings.bones,&settings.tracers,&settings.labels};
void fill(HDC dc,RECT r,COLORREF c){HBRUSH b=CreateSolidBrush(c);FillRect(dc,&r,b);DeleteObject(b);}
void stroke(HDC dc,RECT r,COLORREF c,int radius=0){HPEN p=CreatePen(PS_SOLID,1,c);auto old=SelectObject(dc,p),brush=SelectObject(dc,GetStockObject(NULL_BRUSH));if(radius)RoundRect(dc,r.left,r.top,r.right,r.bottom,radius,radius);else Rectangle(dc,r.left,r.top,r.right,r.bottom);SelectObject(dc,brush);SelectObject(dc,old);DeleteObject(p);}
void segment(HDC dc,int x,int y,int xx,int yy,COLORREF c,int width=1){HPEN p=CreatePen(PS_SOLID,width,c);auto old=SelectObject(dc,p);MoveToEx(dc,x,y,nullptr);LineTo(dc,xx,yy);SelectObject(dc,old);DeleteObject(p);}
void copyText(HDC dc,RECT r,const std::wstring& text,COLORREF c,HFONT font,UINT flags=DT_LEFT|DT_VCENTER|DT_SINGLELINE|DT_END_ELLIPSIS){auto old=SelectObject(dc,font);SetBkMode(dc,TRANSPARENT);SetTextColor(dc,c);int spacing=SetTextCharacterExtra(dc,font==navFont?1:font==titleFont?2:0);DrawTextW(dc,text.c_str(),int(text.size()),&r,flags);SetTextCharacterExtra(dc,spacing);SelectObject(dc,old);}
void icon(HDC dc,int type,int x,int y,COLORREF c){
 auto line=[&](int a,int b,int d,int e){segment(dc,x+a,y+b,x+d,y+e,c);};
 if(type==0){stroke(dc,{x+3,y+3,x+15,y+15},c,12);line(9,0,9,5);line(9,13,9,18);line(0,9,5,9);line(13,9,18,9);}
 if(type==1||type==2){line(1,9,6,4);line(6,4,12,4);line(12,4,17,9);line(17,9,12,14);line(12,14,6,14);line(6,14,1,9);stroke(dc,{x+7,y+7,x+12,y+12},c,5);if(type==1)line(0,0,18,18);}
 if(type==3){for(int yy:{2,7,12}){line(1,yy+3,9,yy-1);line(9,yy-1,17,yy+3);line(17,yy+3,9,yy+7);line(9,yy+7,1,yy+3);}}
 if(type==4){line(4,1,11,1);line(11,1,16,6);line(16,6,16,17);line(16,17,4,17);line(4,17,4,1);line(11,1,11,6);line(11,6,16,6);line(7,10,12,10);line(7,13,12,13);}
 if(type==5){line(9,1,17,12);line(17,12,9,16);line(9,16,1,12);line(1,12,9,1);line(9,1,9,16);line(1,12,13,7);line(17,12,5,7);}
 if(type==6){for(int i=0;i<3;++i){int yy=3+i*6,knob=i==1?12:5;line(1,yy,knob-2,yy);line(knob+2,yy,17,yy);stroke(dc,{x+knob-2,y+yy-2,x+knob+3,y+yy+3},c,4);}}
}
int dividerX(){return 184+(uiWidth-184)/2;}
void section(HDC dc,int x,int y,int right,const wchar_t* title){
 HFONT chosen=(wcschr(title,L'ã')||wcschr(title,L'ç'))?brandFont:sectionFont;HFONT fallback=nullptr;if(chosen==brandFont){fallback=CreateFontW(-18,0,0,0,FW_NORMAL,FALSE,FALSE,FALSE,DEFAULT_CHARSET,OUT_TT_PRECIS,CLIP_DEFAULT_PRECIS,ANTIALIASED_QUALITY,DEFAULT_PITCH,L"Trixie-Plain");chosen=fallback;}auto old=SelectObject(dc,chosen);SIZE size{};GetTextExtentPoint32W(dc,title,int(wcslen(title)),&size);SelectObject(dc,old);
 copyText(dc,{x,y-12,right,y+14},title,theme::text,chosen);segment(dc,x+size.cx+12,y+1,right,y+1,theme::divider);if(fallback)DeleteObject(fallback);
}
void field(HDC dc,RECT r,int value){fill(dc,r,theme::field);stroke(dc,r,theme::fieldBorder,4);copyText(dc,r,std::to_wstring(value),theme::text,menuFont,DT_CENTER|DT_SINGLELINE|DT_VCENTER);}
void place(HWND h,int x,int y,int w,int hh){if(h)MoveWindow(h,x,y,w,hh,TRUE);}
void updatePage(HWND hwnd){
 int leftEnd=dividerX()-20;
 for(size_t i=0;i<checks.size();++i){ShowWindow(checks[i],(i==0?currentPage==0:currentPage==2)?SW_SHOW:SW_HIDE);place(checks[i],210,i==0?133:133+int(i-1)*43,leftEnd-210,30);}
 ShowWindow(radiusEdit,currentPage==6?SW_SHOW:SW_HIDE);ShowWindow(speedEdit,currentPage==6?SW_SHOW:SW_HIDE);
 ShowWindow(smoothEdit,currentPage==0?SW_SHOW:SW_HIDE);for(auto button:targetButtons)ShowWindow(button,currentPage==0?SW_SHOW:SW_HIDE);
 int half=(leftEnd-210-10)/2;place(targetButtons[0],210,223,half,30);place(targetButtons[1],220+half,223,half,30);
 place(smoothEdit,leftEnd-80,310,80,28);place(radiusEdit,leftEnd-80,142,80,28);place(speedEdit,leftEnd-80,195,80,28);
 ShowWindow(languageButton,currentPage==homePage?SW_SHOW:SW_HIDE);ShowWindow(buildButton,currentPage==homePage?SW_SHOW:SW_HIDE);
 place(languageButton,uiWidth-196,134,172,34);place(buildButton,210,387,136,34);
 place(windowButtons[0],uiWidth-124,8,32,29);place(windowButtons[1],uiWidth-88,8,32,29);place(windowButtons[2],uiWidth-52,8,32,29);
 place(returnButton,uiWidth-120,uiHeight-45,100,34);place(footerBuild,uiWidth-191,uiHeight-45,65,34);place(footerExit,uiWidth-238,uiHeight-45,40,34);
 InvalidateRect(hwnd,nullptr,FALSE);for(auto button:navigation)InvalidateRect(button,nullptr,FALSE);
}
LRESULT CALLBACK hoverProc(HWND hwnd,UINT msg,WPARAM wp,LPARAM lp,UINT_PTR,DWORD_PTR){
 if(msg==WM_MOUSEMOVE&&hoveredControl!=hwnd){HWND previous=hoveredControl;hoveredControl=hwnd;if(previous)InvalidateRect(previous,nullptr,FALSE);InvalidateRect(hwnd,nullptr,FALSE);TRACKMOUSEEVENT track{sizeof(track),TME_LEAVE,hwnd,0};TrackMouseEvent(&track);}
 if(msg==WM_MOUSELEAVE){hoveredControl=nullptr;InvalidateRect(hwnd,nullptr,FALSE);}return DefSubclassProc(hwnd,msg,wp,lp);
}
void paintMenu(HDC dc){
 const int split=dividerX(),leftEnd=split-20,right=uiWidth-24,rx=split+20,foot=uiHeight-56;
 fill(dc,{0,0,uiWidth,uiHeight},theme::ground);fill(dc,{0,0,184,foot},theme::rail);segment(dc,183,0,183,foot,theme::divider);
 segment(dc,28,77,66,77,theme::rose,2);
 const wchar_t* titles[]={L"aimbot",L"silent aim",L"visuais",L"offsets",L"perfis",L"extras",L"ajustes",L"home"};
 copyText(dc,{210,20,right-130,61},titles[currentPage],theme::text,titleFont);segment(dc,210,65,302,65,theme::rose,2);
 fill(dc,{uiWidth-130,6,uiWidth-14,40},theme::surface);stroke(dc,{uiWidth-130,6,uiWidth-14,40},theme::divider,8);
 segment(dc,split,90,split,foot-18,theme::divider);
 if(currentPage==homePage){
  section(dc,210,101,leftEnd,L"Sessão");section(dc,rx,101,right,L"Aeon / local");
  COLORREF state=uiGameRunning?theme::sage:theme::rose;fill(dc,{210,135,218,143},state);copyText(dc,{231,124,leftEnd,152},uiGameRunning?L"Blood Strike em execução":L"Blood Strike fechado",theme::text,menuFont);
  copyText(dc,{210,164,leftEnd,191},L"Painel",theme::secondary,menuFont);copyText(dc,{210,196,leftEnd,224},L"Aeon / Blood Strike",theme::text,menuFont);
  copyText(dc,{210,233,leftEnd,260},L"Estado da leitura",theme::secondary,menuFont);copyText(dc,{210,265,leftEnd,292},uiAttached?L"Ativa":L"Aguardando sessão",theme::text,menuFont);
  copyText(dc,{210,296,leftEnd,323},L"Build suportada",theme::secondary,menuFont);copyText(dc,{210,328,leftEnd,351},L"ff080393961ac709",theme::text,menuFont);
  copyText(dc,{210,354,leftEnd,376},L"Windows x64 · leitura externa",theme::secondary,smallFont);
  copyText(dc,{rx,134,uiWidth-204,168},L"Idioma",theme::text,menuFont);
 }else if(currentPage==0){
  section(dc,210,101,leftEnd,L"Mira");section(dc,rx,101,right,L"Ativação");
  copyText(dc,{210,181,leftEnd,208},L"Ponto de mira",theme::secondary,menuFont);
  copyText(dc,{210,268,leftEnd,294},L"Suavidade",theme::secondary,menuFont);field(dc,{leftEnd-80,310,leftEnd,338},settings.smoothMs);
  copyText(dc,{210,310,leftEnd-90,338},L"Tempo (ms)",theme::text,menuFont);copyText(dc,{210,352,leftEnd,380},L"0 = direto · maior = mais suave",theme::secondary,smallFont);
  copyText(dc,{rx,133,right,163},L"Botão direito segurado",theme::text,menuFont);copyText(dc,{rx,185,right,213},L"Troca de alvo",theme::secondary,menuFont);copyText(dc,{rx,218,right,245},L"Pausa de 300 ms",theme::text,menuFont);
  copyText(dc,{rx,277,right,338},L"Cabeça: ponto estimado no modelo. Não corresponde a um bone anatômico confirmado.",theme::secondary,smallFont,DT_LEFT|DT_WORDBREAK);
 }else if(currentPage==2){
  section(dc,210,101,leftEnd,L"Elementos");section(dc,rx,101,right,L"Prévia");
  int cx=(rx+right)/2;COLORREF ink=settings.esp?theme::focus:theme::border;
  stroke(dc,{cx-14,170,cx+14,198},ink,28);segment(dc,cx,198,cx,294,ink);segment(dc,cx,217,cx-37,258,ink);segment(dc,cx,217,cx+37,258,ink);segment(dc,cx,294,cx-29,358,ink);segment(dc,cx,294,cx+29,358,ink);
  if(settings.esp&&settings.boxes)stroke(dc,{cx-46,159,cx+46,366},theme::plum);
  if(settings.esp&&settings.bones){segment(dc,cx,198,cx,294,theme::text,2);segment(dc,cx,217,cx-37,258,theme::text);segment(dc,cx,217,cx+37,258,theme::text);segment(dc,cx,294,cx-29,358,theme::text);segment(dc,cx,294,cx+29,358,theme::text);}
  if(settings.esp&&settings.tracers)segment(dc,cx,429,cx,366,theme::plum);
  if(settings.esp&&settings.labels)copyText(dc,{cx-45,133,cx+45,157},L"hp",theme::text,smallFont,DT_CENTER|DT_SINGLELINE|DT_VCENTER);
  copyText(dc,{rx,449,right,477},L"prévia ilustrativa",theme::secondary,smallFont,DT_CENTER|DT_SINGLELINE|DT_VCENTER);
 }else if(currentPage==3){
  section(dc,210,101,leftEnd,L"Build");section(dc,rx,101,right,L"Compatibilidade");
  copyText(dc,{210,133,leftEnd,163},L"SHA256 da imagem suportada",theme::secondary,menuFont);
  copyText(dc,{210,177,leftEnd,252},L"ff080393961ac709\n090824356621358a\ne4f63dbe1c62ff636\nd528589cd097747",theme::text,smallFont,DT_LEFT|DT_WORDBREAK);
  copyText(dc,{210,287,leftEnd,318},L"Tamanho da imagem: 0x94e9000",theme::text,menuFont);
  copyText(dc,{rx,133,right,235},L"A leitura exige a build correspondente. Os endereços deste projeto são vinculados a essa imagem.",theme::text,menuFont,DT_LEFT|DT_WORDBREAK);
 }else if(currentPage==4){
  section(dc,210,101,leftEnd,L"Calibrações");section(dc,rx,101,right,L"Seleção por zoom");int y=135;
  for(const auto& item:displayedProfiles){copyText(dc,{210,y,leftEnd,y+28},item.first,theme::text,menuFont);copyText(dc,{210,y+29,leftEnd,y+54},L"FOV "+std::to_wstring(item.second.fov).substr(0,5)+L"°",theme::secondary,smallFont);y+=77;}
  if(displayedProfiles.empty())copyText(dc,{210,y,leftEnd,y+80},L"Nenhum perfil medido disponível.",theme::secondary,menuFont,DT_LEFT|DT_WORDBREAK);
  copyText(dc,{rx,135,right,265},L"Os perfis medidos são selecionados pelo campo de visão. Armas com a mesma ampliação podem exigir calibrações distintas.",theme::text,menuFont,DT_LEFT|DT_WORDBREAK);
 }else if(currentPage==5){
  section(dc,210,101,leftEnd,L"Atalhos");section(dc,rx,101,right,L"Controles");
  copyText(dc,{210,137,leftEnd,166},L"Insert",theme::text,menuFont);copyText(dc,{210,171,leftEnd,200},L"Mostrar ou ocultar o painel",theme::secondary,menuFont);
  copyText(dc,{210,231,leftEnd,260},L"F8",theme::text,menuFont);copyText(dc,{210,265,leftEnd,294},L"Encerrar o programa",theme::secondary,menuFont);
  copyText(dc,{rx,137,right,236},L"A mira exige foco no jogo e botão direito pressionado. O menu permanece independente do overlay.",theme::text,menuFont,DT_LEFT|DT_WORDBREAK);
 }else if(currentPage==6){
  section(dc,210,101,leftEnd,L"Resposta");section(dc,rx,101,right,L"Preferências");
  copyText(dc,{210,142,leftEnd-90,170},L"Raio (px)",theme::text,menuFont);field(dc,{leftEnd-80,142,leftEnd,170},settings.radius);
  copyText(dc,{210,195,leftEnd-90,223},L"Velocidade",theme::text,menuFont);field(dc,{leftEnd-80,195,leftEnd,223},settings.speed);
  copyText(dc,{rx,137,right,237},L"As alterações são salvas automaticamente. A suavidade e o ponto de mira ficam na página aimbot.",theme::text,menuFont,DT_LEFT|DT_WORDBREAK);
 }
 fill(dc,{16,foot,uiWidth-16,uiHeight},theme::footer);segment(dc,16,foot,uiWidth-16,foot,theme::divider);
 fill(dc,{20,foot+25,28,foot+33},uiAttached?theme::sage:theme::rose);copyText(dc,{41,foot+12,uiWidth-260,foot+44},uiAttached?L"Conectado":L"Aguardando sessão",theme::text,menuFont);
}
HFONT makeFont(int size,const wchar_t* family,int weight=FW_NORMAL){HFONT f=CreateFontW(-size,0,0,0,weight,FALSE,FALSE,FALSE,DEFAULT_CHARSET,OUT_TT_PRECIS,CLIP_DEFAULT_PRECIS,ANTIALIASED_QUALITY,DEFAULT_PITCH,family);require(f!=nullptr,"font creation");return f;}
void validateFace(HDC dc,HFONT font,const wchar_t* expected){auto old=SelectObject(dc,font);wchar_t actual[128]{};GetTextFaceW(dc,128,actual);SelectObject(dc,old);require(!wcscmp(actual,expected),"reference font substitution");}
LRESULT CALLBACK menuProc(HWND hwnd,UINT msg,WPARAM wp,LPARAM lp){
 switch(msg){
 case WM_CREATE:{
  menuWindow=hwnd;InitCommonControls();fieldBrush=CreateSolidBrush(theme::field);
  menuFont=makeFont(16,L"Georgia");smallFont=makeFont(13,L"Georgia");brandFont=makeFont(42,L"Trixie-Plain");navFont=makeFont(27,L"Narrowband Prime ICG");titleFont=makeFont(36,L"Narrowband Prime ICG");sectionFont=makeFont(18,L"Love Letter Typewriter");actionFont=makeFont(14,L"Georgia",FW_BOLD);
  HDC dc=CreateCompatibleDC(nullptr);validateFace(dc,brandFont,L"Trixie-Plain");validateFace(dc,menuFont,L"Georgia");validateFace(dc,navFont,L"Narrowband Prime ICG");validateFace(dc,actionFont,L"Georgia");DeleteDC(dc);
  atomicFile(appDir/L"branding.json","{\"name\":\"aeon\",\"brand_font\":\"Trixie-Plain\",\"body_font\":\"Georgia\",\"navigation_font\":\"Narrowband Prime ICG\",\"font_loaded\":true,\"design\":\"reference-open-columns\"}\n");
  displayedProfiles.clear();if(fs::exists(appDir/L"calibrations"))for(const auto& entry:fs::directory_iterator(appDir/L"calibrations")){if(entry.path().extension()!=L".json"||displayedProfiles.size()>=64)continue;try{displayedProfiles.emplace_back(entry.path().stem().wstring(),calibration(entry.path()));}catch(const std::exception&) {}}
  auto make=[&](int id,const wchar_t* text,int x,int y,int w,int h){HWND control=CreateWindowW(L"BUTTON",text,WS_CHILD|WS_VISIBLE|WS_TABSTOP|BS_OWNERDRAW,x,y,w,h,hwnd,reinterpret_cast<HMENU>(id),nullptr,nullptr);require(control!=nullptr,"button creation");SetWindowSubclass(control,hoverProc,1,0);return control;};
  logoButton=make(310,L"aeon",26,14,132,58);
  const wchar_t* nav[]={L"aimbot",L"silent aim",L"visuais",L"offsets",L"perfis",L"extras",L"ajustes"};for(int i=0;i<7;++i)navigation[i]=make(300+i,nav[i],24,105+i*48,145,35);EnableWindow(navigation[1],FALSE);
  const wchar_t* names[]={L"Habilitar mira",L"Habilitar ESP",L"Caixas",L"Skeleton",L"Antena",L"HP"};for(int i=0;i<6;++i)checks[i]=make(100+i,names[i],210,133,312,30);
  windowButtons[0]=make(400,L"Minimizar",776,8,32,29);windowButtons[1]=make(402,L"Maximizar ou restaurar",812,8,32,29);windowButtons[2]=make(401,L"Fechar",848,8,32,29);
  auto edit=[&](int id,int value){HWND e=CreateWindowExW(0,L"EDIT",std::to_wstring(value).c_str(),WS_CHILD|WS_TABSTOP|ES_NUMBER|ES_CENTER|WS_BORDER,440,146,80,28,hwnd,reinterpret_cast<HMENU>(id),nullptr,nullptr);require(e!=nullptr,"edit creation");SendMessageW(e,WM_SETFONT,reinterpret_cast<WPARAM>(menuFont),TRUE);return e;};
  radiusEdit=edit(200,settings.radius);speedEdit=edit(201,settings.speed);smoothEdit=edit(202,settings.smoothMs);
  targetButtons[0]=make(500,L"Cabeça (estim.)",210,223,150,30);targetButtons[1]=make(501,L"Corpo",370,223,150,30);
  languageButton=make(702,L"Português (Brasil)",704,134,172,34);buildButton=make(703,L"Ver build",210,387,136,34);
  returnButton=make(704,L"Voltar ao jogo",780,561,100,34);footerBuild=make(705,L"Offsets",709,561,65,34);footerExit=make(706,L"F8",662,561,40,34);
  RegisterHotKey(hwnd,1,MOD_NOREPEAT,VK_INSERT);RegisterHotKey(hwnd,2,MOD_NOREPEAT,VK_F8);SetTimer(hwnd,1,500,nullptr);updatePage(hwnd);return 0;
 }
 case WM_DRAWITEM:{
  auto& d=*reinterpret_cast<DRAWITEMSTRUCT*>(lp);HDC dc=d.hDC;RECT r=d.rcItem;int id=int(d.CtlID);bool over=hoveredControl==d.hwndItem,focus=d.itemState&ODS_FOCUS;wchar_t text[128]{};GetWindowTextW(d.hwndItem,text,128);
  if(id>=300&&id<307){bool active=currentPage==id-300;fill(dc,r,over?theme::navHover:theme::rail);COLORREF c=!IsWindowEnabled(d.hwndItem)?theme::border:active?theme::text:theme::focus;icon(dc,id-300,9,8,c);copyText(dc,{40,0,r.right,35},text,c,navFont);if(active)segment(dc,0,6,0,29,theme::rose,2);}
  else if(id==310){fill(dc,r,theme::rail);auto previous=SetTextCharacterExtra(dc,0);copyText(dc,r,L"aeon",theme::text,brandFont,DT_LEFT|DT_VCENTER|DT_SINGLELINE);SetTextCharacterExtra(dc,previous);}
  else if(id>=100&&id<106){fill(dc,r,over?theme::surface:theme::ground);RECT box{0,7,15,22};bool on=toggles[id-100]->load();fill(dc,box,on?theme::plum:theme::field);stroke(dc,box,focus?theme::focus:theme::border,3);if(on){segment(dc,3,14,6,17,theme::text,2);segment(dc,6,17,12,10,theme::text,2);}copyText(dc,{25,0,r.right,30},text,theme::text,menuFont);}
  else if(id==500||id==501){bool active=(id==500)==settings.head.load();fill(dc,r,active?theme::selected:over?theme::hover:theme::button);stroke(dc,r,active?theme::focus:theme::border,4);copyText(dc,r,text,theme::text,menuFont,DT_CENTER|DT_VCENTER|DT_SINGLELINE);}
  else if(id==400||id==401||id==402){fill(dc,r,over?(id==401?theme::rgb(0x35232d):theme::hover):theme::surface);if(id==400)segment(dc,12,16,20,16,theme::secondary);else if(id==402)stroke(dc,{12,9,20,17},theme::secondary,2);else{segment(dc,12,9,20,17,theme::secondary);segment(dc,20,9,12,17,theme::secondary);}}
  else if(id==705||id==706){fill(dc,r,theme::footer);copyText(dc,r,text,over?theme::text:theme::secondary,menuFont,DT_CENTER|DT_VCENTER|DT_SINGLELINE);}
  else if(id==704){fill(dc,r,over?theme::rgb(0xb5c4ab):theme::sage);copyText(dc,r,text,theme::ground,actionFont,DT_CENTER|DT_VCENTER|DT_SINGLELINE);}
  else{fill(dc,r,over?theme::hover:theme::button);stroke(dc,r,theme::border,4);copyText(dc,{12,0,r.right-(id==702?23:8),r.bottom},text,theme::text,id==703?actionFont:menuFont);if(id==702){segment(dc,r.right-24,15,r.right-19,20,theme::secondary);segment(dc,r.right-19,20,r.right-14,15,theme::secondary);}}
  if(focus)stroke(dc,{r.left+1,r.top+1,r.right-1,r.bottom-1},theme::focus,4);return TRUE;
 }
 case WM_COMMAND:{int id=LOWORD(wp);
  if(id>=100&&id<106&&HIWORD(wp)==BN_CLICKED){auto& flag=*toggles[id-100];flag=!flag.load();saveSettings();InvalidateRect(reinterpret_cast<HWND>(lp),nullptr,FALSE);InvalidateRect(hwnd,nullptr,FALSE);}
  if(id>=300&&id<307&&id!=301&&HIWORD(wp)==BN_CLICKED){currentPage=id-300;updatePage(hwnd);}
  if(id==310){currentPage=homePage;updatePage(hwnd);}
  if((id==500||id==501)&&HIWORD(wp)==BN_CLICKED){settings.head=id==500;saveSettings();for(auto button:targetButtons)InvalidateRect(button,nullptr,FALSE);}
  if(id==400)ShowWindow(hwnd,SW_MINIMIZE);if(id==401||id==706)PostMessageW(hwnd,WM_CLOSE,0,0);if(id==402)ShowWindow(hwnd,IsZoomed(hwnd)?SW_RESTORE:SW_MAXIMIZE);
  if(id==703||id==705){currentPage=3;updatePage(hwnd);}
  if(id==704){HWND game=reinterpret_cast<HWND>(uiGameWindow.load());if(IsWindow(game)){ShowWindow(hwnd,SW_HIDE);SetForegroundWindow(game);}}
  if(id==702){HMENU popup=CreatePopupMenu();AppendMenuW(popup,MF_STRING|MF_CHECKED,1,L"Português (Brasil)");RECT rect;GetWindowRect(languageButton,&rect);TrackPopupMenu(popup,TPM_RETURNCMD,rect.left,rect.bottom,0,hwnd,nullptr);DestroyMenu(popup);}
  if(id>=200&&id<=202&&HIWORD(wp)==EN_CHANGE){wchar_t b[32]{};GetWindowTextW(reinterpret_cast<HWND>(lp),b,32);int n=_wtoi(b),max=id==200?4096:id==201?1000:500;if(n>=(id==202?0:1)&&n<=max){if(id==200)settings.radius=n;else if(id==201)settings.speed=n;else settings.smoothMs=n;saveSettings();}}
  if(id>=200&&id<=202&&HIWORD(wp)==EN_KILLFOCUS)SetWindowTextW(reinterpret_cast<HWND>(lp),std::to_wstring(id==200?settings.radius.load():id==201?settings.speed.load():settings.smoothMs.load()).c_str());return 0;
 }
 case WM_CTLCOLOREDIT:SetTextColor(reinterpret_cast<HDC>(wp),theme::text);SetBkColor(reinterpret_cast<HDC>(wp),theme::field);return reinterpret_cast<LRESULT>(fieldBrush);
 case WM_ERASEBKGND:return 1;
 case WM_PAINT:{PAINTSTRUCT ps;HDC dest=BeginPaint(hwnd,&ps),dc=CreateCompatibleDC(dest);HBITMAP b=CreateCompatibleBitmap(dest,uiWidth,uiHeight);auto old=SelectObject(dc,b);paintMenu(dc);BitBlt(dest,0,0,uiWidth,uiHeight,dc,0,0,SRCCOPY);SelectObject(dc,old);DeleteObject(b);DeleteDC(dc);EndPaint(hwnd,&ps);return 0;}
 case WM_PRINTCLIENT:paintMenu(reinterpret_cast<HDC>(wp));return 0;
 case WM_SIZE:{RECT client;GetClientRect(hwnd,&client);if(client.right>0&&client.bottom>0){uiWidth=client.right;uiHeight=client.bottom;updatePage(hwnd);}return 0;}
 case WM_GETMINMAXINFO:{auto info=reinterpret_cast<MINMAXINFO*>(lp);info->ptMinTrackSize={900,606};MONITORINFO monitor{sizeof(monitor)};if(GetMonitorInfoW(MonitorFromWindow(hwnd,MONITOR_DEFAULTTONEAREST),&monitor)){info->ptMaxPosition={monitor.rcWork.left-monitor.rcMonitor.left,monitor.rcWork.top-monitor.rcMonitor.top};info->ptMaxSize={monitor.rcWork.right-monitor.rcWork.left,monitor.rcWork.bottom-monitor.rcWork.top};}return 0;}
 case WM_NCHITTEST:{POINT pt{short(LOWORD(lp)),short(HIWORD(lp))};ScreenToClient(hwnd,&pt);if(pt.y<80&&pt.x>184&&pt.x<uiWidth-140)return HTCAPTION;return HTCLIENT;}
 case WM_TIMER:InvalidateRect(hwnd,nullptr,FALSE);return 0;
 case WM_HOTKEY:if(wp==1)ShowWindow(hwnd,IsWindowVisible(hwnd)?SW_HIDE:SW_SHOWNORMAL);else if(wp==2)PostMessageW(hwnd,WM_CLOSE,0,0);return 0;
 case WM_CLOSE:settings.running=false;saveSettings();DestroyWindow(hwnd);return 0;
 case WM_DESTROY:KillTimer(hwnd,1);UnregisterHotKey(hwnd,1);UnregisterHotKey(hwnd,2);if(fieldBrush)DeleteObject(fieldBrush);PostQuitMessage(0);return 0;
 }
 return DefWindowProcW(hwnd,msg,wp,lp);
}
void destroyMenuFonts(){for(HFONT font:{menuFont,brandFont,smallFont,navFont,titleFont,sectionFont,actionFont})if(font)DeleteObject(font);}
void renderDesignPreview(){
 BrandTypeface fonts;WNDCLASSW wc{};wc.lpfnWndProc=menuProc;wc.hInstance=GetModuleHandleW(nullptr);wc.lpszClassName=L"Aeon.DesignPreview";require(RegisterClassW(&wc)!=0,"preview class");
 HWND window=CreateWindowW(wc.lpszClassName,L"aeon",WS_POPUP,0,0,900,606,nullptr,nullptr,wc.hInstance,nullptr);require(window!=nullptr,"preview window");
 HDC dc=CreateCompatibleDC(nullptr);BITMAPINFO info{};info.bmiHeader.biSize=40;info.bmiHeader.biWidth=900;info.bmiHeader.biHeight=-606;info.bmiHeader.biPlanes=1;info.bmiHeader.biBitCount=32;void* pixels=nullptr;
 HBITMAP bitmap=CreateDIBSection(dc,&info,DIB_RGB_COLORS,&pixels,nullptr,0);require(bitmap!=nullptr,"preview bitmap");auto previous=SelectObject(dc,bitmap);
 for(auto page:{homePage,0,2}){currentPage=page;updatePage(window);SendMessageW(window,WM_PRINT,reinterpret_cast<WPARAM>(dc),PRF_CLIENT|PRF_CHILDREN|PRF_ERASEBKGND);GdiFlush();
  BITMAPFILEHEADER file{};file.bfType=0x4d42;file.bfOffBits=sizeof(file)+40;file.bfSize=file.bfOffBits+900*606*4;
  std::ofstream out(appDir/(page==homePage?L"design-preview.bmp":page==0?L"design-aim.bmp":L"design-visuals.bmp"),std::ios::binary);out.write(reinterpret_cast<char*>(&file),sizeof(file));out.write(reinterpret_cast<char*>(&info.bmiHeader),40);out.write(static_cast<char*>(pixels),900*606*4);
 }
 SelectObject(dc,previous);DeleteObject(bitmap);DeleteDC(dc);DestroyWindow(window);destroyMenuFonts();
}
