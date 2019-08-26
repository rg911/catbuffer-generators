/**
 * Generator utility class.
 */
export class GeneratorUtils {

	/**
     * Converts a (64bit) uint8 array into a number array.
     * @param {Uint8Array} input A uint8 array.
     * @returns {number[]} The uint64 representation of the input.
     */
    public static bufferToUint64 (input: Uint8Array): number[] {
        if (8 !== input.length) {
            throw Error(`byte array has unexpected size '${input.length}'`);
		}
		input = input.reverse();
        return [GeneratorUtils.readUint32At(input, 0), GeneratorUtils.readUint32At(input, 4)];
	}
	
	/**
     * Read buffer into 32bits integer at given index.
     * @param {Uint8Array} bytes A uint8 array.
	 * @param {number} index Index.
     * @returns {number} 32bits integer.
     */
	public static readUint32At(bytes: Uint8Array, index: number): number {
		return (bytes[index] + (bytes[index + 1] << 8) + (bytes[index + 2] << 16) + (bytes[index + 3] << 24)) >>> 0;
	}

	/**
     * Write uint to buffer
     * @param {number} uintValue A uint8 array.
	 * @param {number} bufferSize Buffer size.
     * @returns {Uint8Array}
     */
	public static uintToBuffer (uintValue: number, bufferSize: number): Uint8Array {
		const buffer = new ArrayBuffer(bufferSize);
		const dataView = new DataView(buffer);
		if (1 === bufferSize)
			dataView.setUint8(0, uintValue);
	
		else if (2 === bufferSize)
			dataView.setUint16(0, uintValue, true);
	
		else if (4 === bufferSize)
			dataView.setUint32(0, uintValue, true);
	
		else
			throw new Error('Unexpected bufferSize');
	
		return new Uint8Array(buffer);
	}

	/**
     * Write uint to buffer
     * @param {Uint8Array} buffer A uint8 array.
     * @returns {number}
     */
	public static bufferToUint(buffer: Uint8Array): number {
		const dataView = new DataView(buffer.buffer);
		if (1 === buffer.byteLength)
			return dataView.getUint8(0);
	
		else if (2 === buffer.byteLength)
			return dataView.getUint16(0, true);
	
		else if (4 === buffer.byteLength)
			return dataView.getUint32(0, true);
	
		throw new Error('Unexpected buffer size');
	};

	/**
     * Write Uint64 to buffer
     * @param {number} uintValue Uint64 (number[]).
     * @returns {Uint8Array}
     */
	public static uint64ToBuffer(uintValue: number[]): Uint8Array {
		const uint32Array = new Uint32Array(uintValue);
		return new Uint8Array(uint32Array.buffer);
	}

	/**
     * Concatenate two arrays
     * @param {Uint8Array} array1 A Uint8Array.
	 * @param {Uint8Array} array2 A Uint8Array.
     * @returns {Uint8Array}
     */
	public static concatTypedArrays(array1: Uint8Array, array2: Uint8Array): Uint8Array {
		const newArray = new Uint8Array(array1.length + array2.length);
		newArray.set(array1);
		newArray.set(array2, array1.length);
		return newArray;
	}

	/** Converts an unsigned byte to a signed byte with the same binary representation.
     * @param {number} input An unsigned byte.
     * @returns {number} A signed byte with the same binary representation as the input.
     *
     */
    public static uint8ToInt8 = (input: number): number => {
        if (0xFF < input) {
            throw Error(`input '${input}' is out of range`);
        }
        return input << 24 >> 24;
    }

	/** Get bytes by given sub array size.
	 * @param {Uint8Array} binary Binary bytes array.
     * @param {number} size Subarray size.
     * @returns {Uint8Array} 
     *
     */
	public static getBytes(binary: Uint8Array, size: number): Uint8Array {
		if (size > binary.length)
			throw new RangeError();

		const bytes = binary.slice(0, size);
		return bytes;
	}
}
