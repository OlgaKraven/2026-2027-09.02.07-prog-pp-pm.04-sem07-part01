const path=require('node:path');
const {pathToFileURL}=require('node:url');
const {chromium}=require('playwright');
(async()=>{
 const root=path.resolve(__dirname,'..');
 const browser=await chromium.launch({headless:true});
 const page=await browser.newPage();
 for(const [input,output] of [['print-method.html','assignment.pdf'],['print-areas.html','guide.pdf']]){
  await page.goto(pathToFileURL(path.join(root,'site',input)).href);
  await page.evaluate(()=>document.fonts.ready);
  await page.pdf({path:path.join(root,'site','downloads',output),printBackground:true,preferCSSPageSize:true,tagged:true,outline:true});
  process.stdout.write(output+' exported\n');
 }
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
