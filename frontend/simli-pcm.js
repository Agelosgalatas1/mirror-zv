// Decode only the bounded PCM WAVs already produced by our checked voice service.
export function wavToPCM(buffer) {
  if (!(buffer instanceof ArrayBuffer) || buffer.byteLength < 44 || buffer.byteLength > 6*1024*1024) throw Error('Invalid WAV');
  const d = new DataView(buffer), tag = p => String.fromCharCode(...new Uint8Array(buffer, p, 4));
  if (tag(0) !== 'RIFF' || tag(8) !== 'WAVE') throw Error('Invalid WAV');
  let fmt, data;
  for (let p=12;p+8<=d.byteLength;) {
    const n=d.getUint32(p+4,true), start=p+8;
    if (start+n>d.byteLength) throw Error('Truncated WAV');
    if (tag(p)==='fmt ' && n>=16) fmt={type:d.getUint16(start,true),channels:d.getUint16(start+2,true),rate:d.getUint32(start+4,true),bits:d.getUint16(start+14,true)};
    if (tag(p)==='data') data={start,n};
    p=start+n+(n%2);
  }
  if (!fmt || !data || fmt.type!==1 || fmt.bits!==16 || ![1,2].includes(fmt.channels) || fmt.rate<8000 || fmt.rate>48000 || data.n%(fmt.channels*2)) throw Error('Unsupported WAV');
  const frames=data.n/(fmt.channels*2), duration=frames/fmt.rate;
  if (duration<.1 || duration>120) throw Error('Invalid WAV duration');
  const count=Math.floor(duration*16000), out=new ArrayBuffer(count*2), target=new DataView(out);
  const at=i=>{let sum=0;for(let c=0;c<fmt.channels;c++)sum+=d.getInt16(data.start+(Math.min(frames-1,i)*fmt.channels+c)*2,true);return sum/fmt.channels};
  for(let i=0;i<count;i++){const p=i*fmt.rate/16000,a=Math.floor(p),v=at(a)+(at(a+1)-at(a))*(p-a);target.setInt16(i*2,Math.max(-32768,Math.min(32767,Math.round(v))),true)}
  return new Uint8Array(out);
}
